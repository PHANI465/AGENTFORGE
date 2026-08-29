package cmd

import (
	"fmt"
	"os"
	"text/tabwriter"

	"github.com/PHANI465/AGENTFORGE/packages/cli-go/internal/client"
	"github.com/spf13/cobra"
)

var agentsCmd = &cobra.Command{
	Use:   "agents",
	Short: "Manage agents",
}

var agentsListCmd = &cobra.Command{
	Use:   "list",
	Short: "List your agents",
	RunE: func(_ *cobra.Command, _ []string) error {
		agents, err := mustClient().ListAgents()
		if err != nil {
			printAPIError(err)
			os.Exit(1)
		}
		if len(agents) == 0 {
			fmt.Println("No agents yet — create one with `agentforge agents create`.")
			return nil
		}

		w := tabwriter.NewWriter(os.Stdout, 0, 2, 2, ' ', 0)
		fmt.Fprintln(w, "ID\tNAME\tMODEL\tSTATUS")
		for _, a := range agents {
			fmt.Fprintf(w, "%s\t%s\t%s\t%s\n", a.ID, a.Name, a.Model, a.Status)
		}
		return w.Flush()
	},
}

var agentsGetCmd = &cobra.Command{
	Use:   "get <agent-id>",
	Short: "Show one agent",
	Args:  cobra.ExactArgs(1),
	RunE: func(_ *cobra.Command, args []string) error {
		agent, err := mustClient().GetAgent(args[0])
		if err != nil {
			printAPIError(err)
			os.Exit(1)
		}
		fmt.Printf("ID:      %s\nName:    %s\nModel:   %s\nStatus:  %s\nPrompt:  %s\n",
			agent.ID, agent.Name, agent.Model, agent.Status, agent.SystemPrompt)
		return nil
	},
}

var (
	createName   string
	createModel  string
	createPrompt string
)

var agentsCreateCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a new agent",
	RunE: func(_ *cobra.Command, _ []string) error {
		if createName == "" || createPrompt == "" {
			return fmt.Errorf("--name and --prompt are required")
		}
		agent, err := mustClient().CreateAgent(client.CreateAgentRequest{
			Name: createName, Model: createModel, SystemPrompt: createPrompt,
		})
		if err != nil {
			printAPIError(err)
			os.Exit(1)
		}
		fmt.Printf("Created agent %s (%s)\n", agent.ID, agent.Name)
		return nil
	},
}

var agentsRunCmd = &cobra.Command{
	Use:   "run <agent-id> <input>",
	Short: "Send a message to an agent and print its response",
	Args:  cobra.ExactArgs(2),
	RunE: func(_ *cobra.Command, args []string) error {
		run, err := mustClient().RunAgent(args[0], args[1])
		if err != nil {
			printAPIError(err)
			os.Exit(1)
		}
		fmt.Printf("[%s]\n%s\n", run.Status, run.Output)
		return nil
	},
}

func init() {
	agentsCreateCmd.Flags().StringVar(&createName, "name", "", "agent name (required)")
	agentsCreateCmd.Flags().StringVar(&createModel, "model", "gpt-4o-mini", "LLM model")
	agentsCreateCmd.Flags().StringVar(&createPrompt, "prompt", "", "system prompt (required)")

	agentsCmd.AddCommand(agentsListCmd, agentsGetCmd, agentsCreateCmd, agentsRunCmd)
	rootCmd.AddCommand(agentsCmd)
}
