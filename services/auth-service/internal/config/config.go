// Package config loads auth-service's settings from environment variables
// — same pattern every other AgentForge service uses (env vars, never
// hardcoded hosts/ports/secrets, per CLAUDE.md's ADR-003 consequence).
package config

import (
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"errors"
	"fmt"
	"os"
	"time"
)

type Config struct {
	PostgresDSN string

	// RS256 keypair for signing/verifying session JWTs. Asymmetric on
	// purpose: this service holds the private key and is the only thing
	// that ever signs a token; every other service verifies using only
	// the public half, fetched from GET /.well-known/jwks.json — no
	// shared signing secret needs to exist anywhere else.
	SigningKey *rsa.PrivateKey
	KeyID      string

	AccessTokenTTL  time.Duration
	RefreshTokenTTL time.Duration

	GitHubClientID     string
	GitHubClientSecret string
	GoogleClientID     string
	GoogleClientSecret string

	// HMAC key for signing the OAuth `state` parameter — a separate secret
	// from SigningKey (RSA, used for session JWTs) since state tokens are
	// symmetric/HMAC by design: they're short-lived, self-verified by this
	// service alone, and never need to be checked by anyone else.
	OAuthStateSecret []byte

	// Where OAuth providers redirect back to, and where the dashboard
	// sends the browser after a successful login — e.g.
	// https://agentforge.example.com/auth/callback and
	// https://agentforge.example.com respectively.
	OAuthRedirectBaseURL string
	DashboardURL         string

	Port string
}

func Load() (Config, error) {
	dsn := os.Getenv("POSTGRES_DSN")
	if dsn == "" {
		return Config{}, errors.New("POSTGRES_DSN is required")
	}

	keyPEM := os.Getenv("AUTH_SIGNING_KEY_PEM")
	if keyPEM == "" {
		return Config{}, errors.New(
			"AUTH_SIGNING_KEY_PEM is required — generate one with: " +
				"openssl genrsa 2048 (PKCS#1 PEM, private key only)")
	}
	key, err := parseRSAPrivateKeyPEM(keyPEM)
	if err != nil {
		return Config{}, fmt.Errorf("parsing AUTH_SIGNING_KEY_PEM: %w", err)
	}

	keyID := os.Getenv("AUTH_SIGNING_KEY_ID")
	if keyID == "" {
		keyID = "agentforge-auth-1" // stable default; rotate by overriding this + the PEM together
	}

	dashboardURL := os.Getenv("DASHBOARD_URL")
	if dashboardURL == "" {
		dashboardURL = "http://localhost:3001"
	}
	redirectBase := os.Getenv("OAUTH_REDIRECT_BASE_URL")
	if redirectBase == "" {
		redirectBase = "http://localhost:8004"
	}

	stateSecret := os.Getenv("OAUTH_STATE_SECRET")
	if stateSecret == "" {
		return Config{}, errors.New(
			"OAUTH_STATE_SECRET is required — any random string " +
				`(e.g. python -c "import secrets; print(secrets.token_urlsafe(32))")`)
	}

	return Config{
		PostgresDSN:          dsn,
		SigningKey:           key,
		KeyID:                keyID,
		AccessTokenTTL:       15 * time.Minute,
		RefreshTokenTTL:      30 * 24 * time.Hour,
		GitHubClientID:       os.Getenv("GITHUB_CLIENT_ID"),
		GitHubClientSecret:   os.Getenv("GITHUB_CLIENT_SECRET"),
		GoogleClientID:       os.Getenv("GOOGLE_CLIENT_ID"),
		GoogleClientSecret:   os.Getenv("GOOGLE_CLIENT_SECRET"),
		OAuthStateSecret:     []byte(stateSecret),
		OAuthRedirectBaseURL: redirectBase,
		DashboardURL:         dashboardURL,
		Port:                 envOr("PORT", "8004"),
	}, nil
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func parseRSAPrivateKeyPEM(raw string) (*rsa.PrivateKey, error) {
	block, _ := pem.Decode([]byte(raw))
	if block == nil {
		return nil, errors.New("no PEM block found")
	}
	// Accept both PKCS#1 ("RSA PRIVATE KEY") and PKCS#8 ("PRIVATE KEY") —
	// openssl genrsa produces the former, many other tools the latter.
	if key, err := x509.ParsePKCS1PrivateKey(block.Bytes); err == nil {
		return key, nil
	}
	parsed, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("not a valid PKCS#1 or PKCS#8 RSA private key: %w", err)
	}
	key, ok := parsed.(*rsa.PrivateKey)
	if !ok {
		return nil, errors.New("PEM key is not an RSA private key")
	}
	return key, nil
}
