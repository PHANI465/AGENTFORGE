package auth

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"errors"
	"fmt"
	"time"

	"golang.org/x/oauth2"
)

// Endpoint URLs are hardcoded (not pulled from golang.org/x/oauth2's
// per-provider subpackages) — these are stable, publicly documented OAuth
// endpoints, and hardcoding them here avoids depending on an exact
// subpackage layout this was written without a Go toolchain available to
// confirm against go.sum.
var (
	githubEndpoint = oauth2.Endpoint{
		AuthURL:  "https://github.com/login/oauth/authorize",
		TokenURL: "https://github.com/login/oauth/access_token",
	}
	googleEndpoint = oauth2.Endpoint{
		AuthURL:  "https://accounts.google.com/o/oauth2/auth",
		TokenURL: "https://oauth2.googleapis.com/token",
	}
)

// ProviderUser is the subset of an OAuth provider's userinfo response this
// service actually needs, normalized across providers.
type ProviderUser struct {
	Subject string // provider's stable user ID — never the email (emails can change/be reused)
	Email   string
	Name    string
}

func GitHubOAuthConfig(clientID, clientSecret, redirectURL string) *oauth2.Config {
	return &oauth2.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		RedirectURL:  redirectURL,
		Scopes:       []string{"read:user", "user:email"},
		Endpoint:     githubEndpoint,
	}
}

func GoogleOAuthConfig(clientID, clientSecret, redirectURL string) *oauth2.Config {
	return &oauth2.Config{
		ClientID:     clientID,
		ClientSecret: clientSecret,
		RedirectURL:  redirectURL,
		Scopes:       []string{"https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"},
		Endpoint:     googleEndpoint,
	}
}

// --- Stateless CSRF state token ---
//
// The OAuth `state` parameter must be unguessable and tied to this
// specific login attempt, or an attacker can trick a victim into
// completing an OAuth flow the attacker initiated (login CSRF). Rather
// than storing state server-side (a session store, Redis, a DB row —
// more infra for a single-instance-friendly stateless service), this
// signs a timestamp with an HMAC and treats "valid signature + not
// expired" as sufficient: the state never needs to be looked up, only
// verified, and it's single-purpose (just proves *this service* issued
// it recently), not a general session token.

const stateTTL = 10 * time.Minute

func GenerateState(secret []byte) string {
	ts := time.Now().Unix()
	tsBytes := make([]byte, 8)
	binary.BigEndian.PutUint64(tsBytes, uint64(ts))

	mac := hmac.New(sha256.New, secret)
	mac.Write(tsBytes)
	sig := mac.Sum(nil)

	payload := append(tsBytes, sig...)
	return base64.RawURLEncoding.EncodeToString(payload)
}

func ValidateState(secret []byte, state string) error {
	payload, err := base64.RawURLEncoding.DecodeString(state)
	if err != nil {
		return fmt.Errorf("malformed state: %w", err)
	}
	if len(payload) != 8+sha256.Size {
		return errors.New("malformed state: wrong length")
	}
	tsBytes, sig := payload[:8], payload[8:]

	mac := hmac.New(sha256.New, secret)
	mac.Write(tsBytes)
	expected := mac.Sum(nil)
	if !hmac.Equal(sig, expected) {
		return errors.New("state signature mismatch")
	}

	ts := int64(binary.BigEndian.Uint64(tsBytes))
	if time.Since(time.Unix(ts, 0)) > stateTTL {
		return errors.New("state expired")
	}
	return nil
}
