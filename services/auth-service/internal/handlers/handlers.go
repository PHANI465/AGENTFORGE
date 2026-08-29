// Package handlers wires HTTP requests to the auth logic in internal/auth
// and internal/db. Every response uses the same {"data": ...} / {"error":
// {"code", "message"}} envelope the rest of AgentForge's API uses
// (agentforge_common.envelope) so the dashboard can handle auth-service
// and api-gateway responses identically.
package handlers

import (
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"time"

	"github.com/PHANI465/AGENTFORGE/services/auth-service/internal/auth"
	"github.com/PHANI465/AGENTFORGE/services/auth-service/internal/config"
	"github.com/PHANI465/AGENTFORGE/services/auth-service/internal/db"
	"github.com/google/uuid"
)

type Server struct {
	DB     *db.DB
	Tokens *auth.TokenIssuer
	Cfg    config.Config
}

func NewMux(s *Server) *http.ServeMux {
	mux := http.NewServeMux()

	// /health and /.well-known/jwks.json are deliberately NOT under /auth:
	// kubelet's liveness/readiness probes hit the pod directly on its own
	// port (see infra/helm/agentforge/templates/deployment.yaml), and
	// other services fetch the JWKS via the in-cluster ClusterIP Service
	// (http://auth-service:8004/...) — neither goes through the public
	// Ingress, so neither needs the ingressPath prefix below.
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("GET /.well-known/jwks.json", s.handleJWKS)

	// Everything a browser hits directly (signup/login calls from the
	// dashboard's JS, and OAuth provider redirects) goes through the
	// public Ingress, which forwards the full path unchanged — ALB
	// doesn't rewrite/strip the ingressPath prefix the way nginx-ingress
	// can, so these routes have to include /auth themselves to match what
	// actually arrives (see values.yaml's services.auth-service.ingressPath).
	mux.HandleFunc("POST /auth/signup", s.handleSignup)
	mux.HandleFunc("POST /auth/login", s.handleLogin)
	mux.HandleFunc("POST /auth/token/refresh", s.handleRefresh)
	mux.HandleFunc("GET /auth/oauth/{provider}/login", s.handleOAuthLogin)
	mux.HandleFunc("GET /auth/oauth/{provider}/callback", s.handleOAuthCallback)
	return mux
}

// --- envelope helpers ---

type dataEnvelope struct {
	Data any `json:"data"`
}

type errorEnvelope struct {
	Error struct {
		Code    string `json:"code"`
		Message string `json:"message"`
	} `json:"error"`
}

func writeData(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(dataEnvelope{Data: data})
}

func writeError(w http.ResponseWriter, status int, code, message string) {
	var body errorEnvelope
	body.Error.Code = code
	body.Error.Message = message
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

// --- handlers ---

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	status := "ok"
	if err := s.DB.Ping(ctx); err != nil {
		status = "degraded"
	}
	writeData(w, http.StatusOK, map[string]string{"status": status})
}

func (s *Server) handleJWKS(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "public, max-age=3600")
	_ = json.NewEncoder(w).Encode(s.Tokens.JWKS())
}

type signupRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

type authResponse struct {
	AccessToken  string `json:"access_token"`
	RefreshToken string `json:"refresh_token"`
	UserID       string `json:"user_id"`
	Email        string `json:"email"`
}

func (s *Server) handleSignup(w http.ResponseWriter, r *http.Request) {
	var req signupRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusUnprocessableEntity, "validation_error", "invalid request body")
		return
	}
	if len(req.Email) < 3 || len(req.Password) < 8 {
		writeError(w, http.StatusUnprocessableEntity, "validation_error",
			"email is required and password must be at least 8 characters")
		return
	}

	hash, err := auth.HashPassword(req.Password)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "could not process password")
		return
	}

	userID := uuid.NewString()
	user, err := s.DB.CreateUserWithPassword(r.Context(), userID, req.Email, hash)
	if errors.Is(err, db.ErrEmailTaken) {
		writeError(w, http.StatusConflict, "conflict", "an account with this email already exists")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "could not create account")
		return
	}

	s.respondWithTokens(w, user)
}

type loginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

func (s *Server) handleLogin(w http.ResponseWriter, r *http.Request) {
	var req loginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusUnprocessableEntity, "validation_error", "invalid request body")
		return
	}

	user, err := s.DB.GetUserByEmail(r.Context(), req.Email)
	if errors.Is(err, db.ErrNotFound) {
		// Same message as a wrong password — don't let this endpoint
		// confirm which emails have accounts.
		writeError(w, http.StatusUnauthorized, "unauthorized", "invalid email or password")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "could not process login")
		return
	}
	if user.PasswordHash == nil || !auth.VerifyPassword(*user.PasswordHash, req.Password) {
		writeError(w, http.StatusUnauthorized, "unauthorized", "invalid email or password")
		return
	}

	s.respondWithTokens(w, user)
}

type refreshRequest struct {
	RefreshToken string `json:"refresh_token"`
}

func (s *Server) handleRefresh(w http.ResponseWriter, r *http.Request) {
	var req refreshRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusUnprocessableEntity, "validation_error", "invalid request body")
		return
	}

	claims, err := s.Tokens.ParseRefreshToken(req.RefreshToken)
	if err != nil {
		writeError(w, http.StatusUnauthorized, "unauthorized", "invalid or expired refresh token")
		return
	}

	user, err := s.DB.GetUserByID(r.Context(), claims.Subject)
	if err != nil {
		writeError(w, http.StatusUnauthorized, "unauthorized", "account no longer exists")
		return
	}

	s.respondWithTokens(w, user)
}

func (s *Server) respondWithTokens(w http.ResponseWriter, user db.User) {
	access, err := s.Tokens.IssueAccessToken(user.ID, user.Email)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "could not issue token")
		return
	}
	refresh, err := s.Tokens.IssueRefreshToken(user.ID, user.Email)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "could not issue token")
		return
	}
	writeData(w, http.StatusOK, authResponse{
		AccessToken: access, RefreshToken: refresh, UserID: user.ID, Email: user.Email,
	})
}
