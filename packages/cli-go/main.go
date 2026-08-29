// Command agentforge is a standalone CLI client for the AgentForge API
// Gateway's public REST API. It is not a deployed service — it only ever
// talks to api-gateway over HTTPS with an X-API-Key, the same contract
// the dashboard and the (deprecated) Python SDK stub used.
package main

import "github.com/PHANI465/AGENTFORGE/packages/cli-go/cmd"

func main() {
	cmd.Execute()
}
