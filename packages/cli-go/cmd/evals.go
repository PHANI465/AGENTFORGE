package cmd

import (
	"encoding/json"
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var evalsCmd = &cobra.Command{
	Use:   "evals",
	Short: "Run evaluation suites",
}

var evalsRunCmd = &cobra.Command{
	Use:   "run <suite-id>",
	Short: "Run an eval suite and print its scored summary",
	Args:  cobra.ExactArgs(1),
	RunE: func(_ *cobra.Command, args []string) error {
		evalRun, err := mustClient().RunEvalSuite(args[0])
		if err != nil {
			printAPIError(err)
			os.Exit(1)
		}
		fmt.Printf("Eval run %s [%s]\n", evalRun.ID, evalRun.Status)
		if evalRun.Summary != nil {
			summary, _ := json.MarshalIndent(evalRun.Summary, "", "  ")
			fmt.Println(string(summary))
		}
		return nil
	},
}

func init() {
	evalsCmd.AddCommand(evalsRunCmd)
	rootCmd.AddCommand(evalsCmd)
}
