package auth

import (
	"crypto/rsa"
	"encoding/base64"
	"errors"
	"fmt"
	"math/big"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// Claims embedded in every access token this service issues. Other
// services verify these locally against the public key from
// GET /.well-known/jwks.json — no call back to auth-service per request.
type Claims struct {
	jwt.RegisteredClaims
	Email string `json:"email"`
}

type TokenIssuer struct {
	privateKey *rsa.PrivateKey
	keyID      string
	accessTTL  time.Duration
	refreshTTL time.Duration
}

func NewTokenIssuer(key *rsa.PrivateKey, keyID string, accessTTL, refreshTTL time.Duration) *TokenIssuer {
	return &TokenIssuer{privateKey: key, keyID: keyID, accessTTL: accessTTL, refreshTTL: refreshTTL}
}

func (t *TokenIssuer) sign(userID, email string, ttl time.Duration, tokenType string) (string, error) {
	now := time.Now()
	claims := Claims{
		RegisteredClaims: jwt.RegisteredClaims{
			Subject:   userID,
			IssuedAt:  jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(ttl)),
			Issuer:    "agentforge-auth-service",
			ID:        tokenType, // "access" or "refresh" — checked on refresh so an access token can't be replayed as a refresh token
		},
		Email: email,
	}
	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	token.Header["kid"] = t.keyID
	return token.SignedString(t.privateKey)
}

func (t *TokenIssuer) IssueAccessToken(userID, email string) (string, error) {
	return t.sign(userID, email, t.accessTTL, "access")
}

func (t *TokenIssuer) IssueRefreshToken(userID, email string) (string, error) {
	return t.sign(userID, email, t.refreshTTL, "refresh")
}

var ErrWrongTokenType = errors.New("token is not the expected type")

// ParseRefreshToken verifies signature + expiry and confirms this is
// actually a refresh token (jti == "refresh"), not an access token being
// replayed to mint new tokens forever.
func (t *TokenIssuer) ParseRefreshToken(raw string) (*Claims, error) {
	claims, err := t.parse(raw)
	if err != nil {
		return nil, err
	}
	if claims.ID != "refresh" {
		return nil, ErrWrongTokenType
	}
	return claims, nil
}

func (t *TokenIssuer) parse(raw string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(raw, &Claims{}, func(tok *jwt.Token) (any, error) {
		if _, ok := tok.Method.(*jwt.SigningMethodRSA); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", tok.Header["alg"])
		}
		return &t.privateKey.PublicKey, nil
	})
	if err != nil {
		return nil, err
	}
	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, errors.New("invalid token")
	}
	return claims, nil
}

// JWKS returns the public key in JSON Web Key Set format, for
// GET /.well-known/jwks.json — this is the only thing other services need
// to verify tokens this service issues; the private key never leaves here.
func (t *TokenIssuer) JWKS() map[string]any {
	pub := &t.privateKey.PublicKey
	n := base64.RawURLEncoding.EncodeToString(pub.N.Bytes())
	e := base64.RawURLEncoding.EncodeToString(big.NewInt(int64(pub.E)).Bytes())

	return map[string]any{
		"keys": []map[string]any{
			{
				"kty": "RSA",
				"use": "sig",
				"alg": "RS256",
				"kid": t.keyID,
				"n":   n,
				"e":   e,
			},
		},
	}
}
