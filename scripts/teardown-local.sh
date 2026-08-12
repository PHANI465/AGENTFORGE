#!/usr/bin/env bash
# Tears down the local docker-compose stack, including named volumes
# (postgres_data, prometheus_data, grafana_data) — this deletes local
# Postgres data, so it prompts before running.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "This will stop all AgentForge containers and DELETE local volumes:"
echo "  - postgres_data (all agents/runs/eval history)"
echo "  - prometheus_data, grafana_data"
read -r -p "Continue? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted."
  exit 1
fi

docker compose -f infra/docker/docker-compose.yml down -v

echo "Done. Bring it back up with:"
echo "  docker compose -f infra/docker/docker-compose.yml --env-file .env up -d"
