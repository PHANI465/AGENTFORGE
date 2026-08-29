package cmd

import (
	"fmt"
	"os"

	"github.com/PHANI465/AGENTFORGE/packages/cli-go/internal/client"
	"github.com/PHANI465/AGENTFORGE/packages/cli-go/internal/config"
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "agentforge",
	Short: "Command-line client for the AgentForge API",
	Long: "agentforge talks to a running AgentForge API Gateway over its public REST API " +
		"— the same contract the dashboard and Python SDK use. Run `agentforge login` first.",
}

// Execute runs the CLI; called from main.go.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}

// mustClient loads the saved config and exits with a clear message if
// `agentforge login` hasn't been run yet, rather than failing deep inside
// an HTTP call with a confusing 401.
func mustClient() *client.Client {
	cfg, err := config.Load()
	if err != nil {
		fmt.Fprintln(os.Stderr, "error reading config:", err)
		os.Exit(1)
	}
	if cfg.APIKey == "" {
		fmt.Fprintln(os.Stderr, "not logged in — run `agentforge login` first")
		os.Exit(1)
	}
	return client.New(cfg.APIURL, cfg.APIKey)
}

// printAPIError writes a clean one-line message for API errors instead of
// a raw Go error dump, using the same code/message the dashboard surfaces.
func printAPIError(err error) {
	if apiErr, ok := err.(*client.APIError); ok {
		fmt.Fprintf(os.Stderr, "error: %s\n", apiErr.Message)
		return
	}
	fmt.Fprintln(os.Stderr, "error:", err)
}
