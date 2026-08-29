package cmd

import (
	"fmt"
	"os"

	"github.com/PHANI465/AGENTFORGE/packages/cli-go/internal/client"
	"github.com/PHANI465/AGENTFORGE/packages/cli-go/internal/config"
	"github.com/spf13/cobra"
)

var (
	loginAPIURL string
	loginAPIKey string
)

var loginCmd = &cobra.Command{
	Use:   "login",
	Short: "Save an API URL and key for future commands",
	Long: "Verifies the URL/key actually work (a single GET /api/v1/agents call) before saving, " +
		"so a typo shows up here instead of on every later command.",
	RunE: func(_ *cobra.Command, _ []string) error {
		if loginAPIURL == "" || loginAPIKey == "" {
			return fmt.Errorf("both --url and --key are required")
		}

		c := client.New(loginAPIURL, loginAPIKey)
		if err := c.Ping(); err != nil {
			return fmt.Errorf("could not authenticate against %s: %w", loginAPIURL, err)
		}

		if err := config.Save(config.Config{APIURL: loginAPIURL, APIKey: loginAPIKey}); err != nil {
			return err
		}

		fmt.Fprintf(os.Stdout, "Logged in to %s\n", loginAPIURL)
		return nil
	},
}

func init() {
	loginCmd.Flags().StringVar(&loginAPIURL, "url", "http://localhost:8000", "API Gateway base URL")
	loginCmd.Flags().StringVar(&loginAPIKey, "key", "", "API key (X-API-Key)")
	rootCmd.AddCommand(loginCmd)
}
