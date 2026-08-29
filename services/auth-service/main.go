// Command auth-service is AgentForge's identity provider: signup/login
// (email+password and OAuth) and RS256 session token issuance. It owns no
// schema of its own — it reads/writes the `users` table Alembic created
// (packages/common/alembic/versions/0003_add_tenancy.py) via the same
// Postgres every other service uses. Every other service verifies the
// tokens this issues locally, against the public key at
// GET /.well-known/jwks.json — this service is never on the hot path of a
// normal API request, only login/signup/refresh.
package main

import (
	"context"
	"log"
	"net/http"
	"os/signal"
	"syscall"
	"time"

	"github.com/PHANI465/AGENTFORGE/services/auth-service/internal/auth"
	"github.com/PHANI465/AGENTFORGE/services/auth-service/internal/config"
	"github.com/PHANI465/AGENTFORGE/services/auth-service/internal/db"
	"github.com/PHANI465/AGENTFORGE/services/auth-service/internal/handlers"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("config error: %v", err)
	}

	database, err := db.Connect(ctx, cfg.PostgresDSN)
	if err != nil {
		log.Fatalf("database error: %v", err)
	}
	defer database.Close()

	tokens := auth.NewTokenIssuer(cfg.SigningKey, cfg.KeyID, cfg.AccessTokenTTL, cfg.RefreshTokenTTL)

	server := &handlers.Server{DB: database, Tokens: tokens, Cfg: cfg}
	httpServer := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      handlers.NewMux(server),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	go func() {
		<-ctx.Done()
		log.Println("shutting down")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = httpServer.Shutdown(shutdownCtx)
	}()

	log.Printf("auth-service listening on :%s", cfg.Port)
	if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("server error: %v", err)
	}
}
