package auth

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"

	"golang.org/x/oauth2"
)

// FetchGitHubUser calls GitHub's userinfo API with the token from the
// OAuth exchange. GitHub's /user endpoint can return a null email for
// accounts with a private email setting, so this falls back to
// /user/emails and picks the primary, verified one.
func FetchGitHubUser(ctx context.Context, cfg *oauth2.Config, token *oauth2.Token) (ProviderUser, error) {
	client := cfg.Client(ctx, token)

	var profile struct {
		ID    int64   `json:"id"`
		Login string  `json:"login"`
		Name  string  `json:"name"`
		Email *string `json:"email"`
	}
	if err := getJSON(client, "https://api.github.com/user", &profile); err != nil {
		return ProviderUser{}, fmt.Errorf("fetching github profile: %w", err)
	}

	email := ""
	if profile.Email != nil {
		email = *profile.Email
	}
	if email == "" {
		var emails []struct {
			Email    string `json:"email"`
			Primary  bool   `json:"primary"`
			Verified bool   `json:"verified"`
		}
		if err := getJSON(client, "https://api.github.com/user/emails", &emails); err != nil {
			return ProviderUser{}, fmt.Errorf("fetching github emails: %w", err)
		}
		for _, e := range emails {
			if e.Primary && e.Verified {
				email = e.Email
				break
			}
		}
	}
	if email == "" {
		return ProviderUser{}, fmt.Errorf("github account has no verified primary email")
	}

	name := profile.Name
	if name == "" {
		name = profile.Login
	}

	return ProviderUser{
		Subject: strconv.FormatInt(profile.ID, 10),
		Email:   email,
		Name:    name,
	}, nil
}

// FetchGoogleUser calls Google's OpenID Connect userinfo endpoint.
func FetchGoogleUser(ctx context.Context, cfg *oauth2.Config, token *oauth2.Token) (ProviderUser, error) {
	client := cfg.Client(ctx, token)

	var profile struct {
		Sub           string `json:"sub"`
		Email         string `json:"email"`
		EmailVerified bool   `json:"email_verified"`
		Name          string `json:"name"`
	}
	if err := getJSON(client, "https://www.googleapis.com/oauth2/v3/userinfo", &profile); err != nil {
		return ProviderUser{}, fmt.Errorf("fetching google profile: %w", err)
	}
	if !profile.EmailVerified {
		return ProviderUser{}, fmt.Errorf("google account email is not verified")
	}

	return ProviderUser{
		Subject: profile.Sub,
		Email:   profile.Email,
		Name:    profile.Name,
	}, nil
}

func getJSON(client *http.Client, url string, out any) error {
	resp, err := client.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status %d from %s", resp.StatusCode, url)
	}
	return json.NewDecoder(resp.Body).Decode(out)
}
