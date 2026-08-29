package handlers

import (
	"fmt"
	"net/http"
	"net/url"

	"github.com/PHANI465/AGENTFORGE/services/auth-service/internal/auth"
	"github.com/google/uuid"
	"golang.org/x/oauth2"
)

func (s *Server) providerConfig(provider string) (*oauth2.Config, error) {
	// Must match the route registered in NewMux exactly — /auth/oauth/...,
	// not /oauth/..., since that's the path the public Ingress actually
	// forwards (see NewMux's comment on why).
	redirectURL := s.Cfg.OAuthRedirectBaseURL + "/auth/oauth/" + provider + "/callback"
	switch provider {
	case "github":
		if s.Cfg.GitHubClientID == "" {
			return nil, fmt.Errorf("github OAuth is not configured")
		}
		return auth.GitHubOAuthConfig(s.Cfg.GitHubClientID, s.Cfg.GitHubClientSecret, redirectURL), nil
	case "google":
		if s.Cfg.GoogleClientID == "" {
			return nil, fmt.Errorf("google OAuth is not configured")
		}
		return auth.GoogleOAuthConfig(s.Cfg.GoogleClientID, s.Cfg.GoogleClientSecret, redirectURL), nil
	default:
		return nil, fmt.Errorf("unknown provider %q", provider)
	}
}

// handleOAuthLogin redirects the browser to the provider's consent screen.
// GET so a plain link/redirect from the dashboard works with no JS needed.
func (s *Server) handleOAuthLogin(w http.ResponseWriter, r *http.Request) {
	provider := r.PathValue("provider")
	cfg, err := s.providerConfig(provider)
	if err != nil {
		writeError(w, http.StatusNotFound, "not_found", err.Error())
		return
	}

	state := auth.GenerateState(s.Cfg.OAuthStateSecret)
	http.Redirect(w, r, cfg.AuthCodeURL(state), http.StatusFound)
}

// handleOAuthCallback is where the provider redirects back with a code.
// On success it redirects the browser to the dashboard with tokens in the
// URL fragment (#access_token=...) — a fragment, not a query string, so
// the tokens never get logged by any server (browsers don't send the
// fragment in the request at all) between here and the dashboard's own JS
// picking them up.
func (s *Server) handleOAuthCallback(w http.ResponseWriter, r *http.Request) {
	provider := r.PathValue("provider")
	cfg, err := s.providerConfig(provider)
	if err != nil {
		writeError(w, http.StatusNotFound, "not_found", err.Error())
		return
	}

	if err := auth.ValidateState(s.Cfg.OAuthStateSecret, r.URL.Query().Get("state")); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_state", "OAuth state is invalid or expired — please try logging in again")
		return
	}

	code := r.URL.Query().Get("code")
	if code == "" {
		writeError(w, http.StatusBadRequest, "invalid_request", "missing authorization code")
		return
	}

	token, err := cfg.Exchange(r.Context(), code)
	if err != nil {
		writeError(w, http.StatusBadGateway, "oauth_exchange_failed", "could not exchange authorization code")
		return
	}

	var providerUser auth.ProviderUser
	switch provider {
	case "github":
		providerUser, err = auth.FetchGitHubUser(r.Context(), cfg, token)
	case "google":
		providerUser, err = auth.FetchGoogleUser(r.Context(), cfg, token)
	}
	if err != nil {
		writeError(w, http.StatusBadGateway, "oauth_userinfo_failed", err.Error())
		return
	}

	userID := uuid.NewString()
	user, err := s.DB.FindOrCreateOAuthUser(
		r.Context(), userID, provider, providerUser.Subject, providerUser.Email, providerUser.Name,
	)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "internal_error", "could not complete login")
		return
	}

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

	dest := s.Cfg.DashboardURL + "/auth/callback#" + url.Values{
		"access_token":  {access},
		"refresh_token": {refresh},
	}.Encode()
	http.Redirect(w, r, dest, http.StatusFound)
}
