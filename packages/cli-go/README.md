# agentforge CLI (Go)

A standalone command-line client for the AgentForge API Gateway — talks
only to its public REST API (`X-API-Key` over HTTPS), the same contract
the dashboard and SDK use. It is not a deployed service and isn't part of
the Python `uv` workspace; it's a separate Go module, built and tested
independently.

## Build

```bash
go build -o agentforge .
```

(First run: `go mod tidy` to resolve dependencies and generate `go.sum` —
not committed yet since this was written without a local Go toolchain
available to run it.)

## Usage

```bash
agentforge login --url http://localhost:8000 --key afk_...
agentforge agents list
agentforge agents create --name my-agent --prompt "Be concise."
agentforge agents run <agent-id> "What's the weather in SF?"
agentforge evals run <suite-id>
```

Config is saved to `~/.agentforge/config.json` (mode `0600`).

## Why Go, and why a CLI first

See `docs/PROJECT_DOSSIER.md`'s ecosystem section: Go is the standard
choice for this kind of tool (`kubectl`, `gh`, `terraform` are all Go) —
single static binary, fast builds, no runtime dependency for whoever
installs it. This retires `packages/sdk/agentforge/cli.py`, a registered
console script that only ever printed "not yet implemented."
