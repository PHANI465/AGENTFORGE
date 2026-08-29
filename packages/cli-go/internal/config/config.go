// Package config reads and writes the CLI's local config file — the API
// base URL and API key set by `agentforge login`, stored so every other
// command doesn't need them passed in every time.
package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type Config struct {
	APIURL string `json:"api_url"`
	APIKey string `json:"api_key"`
}

func path() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("resolving home directory: %w", err)
	}
	return filepath.Join(home, ".agentforge", "config.json"), nil
}

// Load reads the saved config. Returns a zero-value Config (no error) if
// the file doesn't exist yet — callers should check APIKey == "" rather
// than treating "not logged in" as an error.
func Load() (Config, error) {
	p, err := path()
	if err != nil {
		return Config{}, err
	}

	data, err := os.ReadFile(p)
	if os.IsNotExist(err) {
		return Config{}, nil
	}
	if err != nil {
		return Config{}, fmt.Errorf("reading %s: %w", p, err)
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, fmt.Errorf("parsing %s: %w", p, err)
	}
	return cfg, nil
}

// Save writes the config, creating ~/.agentforge if needed.
func Save(cfg Config) error {
	p, err := path()
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(p), 0o700); err != nil {
		return fmt.Errorf("creating config dir: %w", err)
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return fmt.Errorf("encoding config: %w", err)
	}
	// 0600: the file holds a live API key.
	if err := os.WriteFile(p, data, 0o600); err != nil {
		return fmt.Errorf("writing %s: %w", p, err)
	}
	return nil
}
