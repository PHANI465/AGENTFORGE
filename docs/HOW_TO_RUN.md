# How to Run AgentForge — Step-by-Step Guide

> A detailed, beginner-friendly walkthrough for getting the entire AgentForge
> platform running on your machine. Every step explains **what to do**,
> **what command to run**, and **what you have actually achieved** once it
> succeeds — so you understand the system as you bring it up, not just
> copy-paste commands blindly.

---

## Before You Start: What You're About to Build

By the end of this guide, you will have **9 separate programs (containers)**
running together on your laptop, talking to each other over a private
network, forming one working platform:

1. A database (PostgreSQL)
2. A cache (Redis)
3. Four backend services (API Gateway, Agent Runtime, Eval Service, Trace Collector)
4. A metrics collector (Prometheus)
5. A dashboard for metrics (Grafana)
6. A web UI (the React Dashboard)

All of this costs **$0** — everything runs locally. The only cost you might
incur is from OpenAI, and only if you actually run an agent (each run costs
roughly $0.0001–$0.001).

---

## Step 0: Install the Prerequisites

### What to do

Install these three tools if you don't already have them:

| Tool | What It's For | Where to Get It |
|---|---|---|
| **Docker Desktop** | Runs all 9 containers | https://www.docker.com/products/docker-desktop |
| **uv** | Manages Python dependencies and runs Python scripts | https://docs.astral.sh/uv/getting-started/installation/ |
| **Node.js 22** *(optional)* | Only needed if you want to edit the dashboard's frontend code directly (not needed to just run it) | https://nodejs.org/ |

On Windows, after installing Docker Desktop, make sure it's actually running
(check the system tray for the whale icon) before continuing — every command
below will fail silently or with a confusing error if Docker isn't started.

### What you've achieved

Your machine now has the tools needed to build and run every piece of the
platform. Docker is the most important one — it's the engine that will run
all 9 containers identically to how they'd run in production.

---

## Step 1: Get the Code

### What to do

```bash
git clone https://github.com/PHANI465/AGENTFORGE.git
cd AGENTFORGE
```

If you already have the code locally (as you do), just navigate to the
project folder instead:

```bash
cd "E:/PHANI/Main Project ( AgentForce )"
```

### What you've achieved

You have a local copy of the entire monorepo — 4 backend services, the
dashboard, the shared Python packages, the infrastructure code, and all
documentation, all in one folder, all version-controlled with git.

---

## Step 2: Configure Your Environment Variables

### What to do

Copy the example environment file to a real one:

```bash
cp .env.example .env
```

Open `.env` in a text editor and fill in your OpenAI API key:

```
OPENAI_API_KEY=sk-...your-real-key-here...
```

You can get a key from https://platform.openai.com/api-keys if you don't
have one. Everything else in `.env` already has sensible defaults for local
development (database credentials, ports, etc.) — you don't need to touch
them.

**Important**: `.env` is in `.gitignore` — it will never be committed to
git. This is intentional; it's where your real secrets live, separate from
`.env.example` (which has no real values and *is* committed, as a template).

### What you've achieved

You've told the platform which OpenAI account to bill when an agent makes an
LLM call — this is the **BYOK (Bring Your Own Key)** model in action. Nobody
else's credentials are involved; you control your own spend directly. You've
also set up the default connection strings for Postgres and Redis that the
containers will use to find each other.

---

## Step 3: Start the Full Docker Compose Stack

### What to do

```bash
docker compose -f infra/docker/docker-compose.yml --env-file .env up -d
```

Let's break this command down piece by piece, since it's the single most
important command in this whole guide:

| Part | Meaning |
|---|---|
| `docker compose` | The tool that reads a compose file and manages multiple containers together |
| `-f infra/docker/docker-compose.yml` | "Use this specific compose file" (it's not in the root directory) |
| `--env-file .env` | **Critical**: explicitly tells Docker Compose to read your `.env` file for variables like `OPENAI_API_KEY`. If you forget this flag, your containers will start but won't have your API key — this exact mistake happened twice during this project's development (see `MILESTONES.md`) |
| `up` | Start all the services defined in the compose file |
| `-d` | "Detached" — run in the background so your terminal isn't stuck showing logs forever |

The first time you run this, Docker will need to **build** the 4 custom
Python service images and the dashboard image from scratch (using the
Dockerfiles in each service's folder). This downloads base images and
installs dependencies, so it can take a few minutes. Every subsequent
`up -d` will be much faster because Docker caches the layers that haven't
changed.

### How to watch it work (optional but recommended for beginners)

In a separate terminal, watch the containers start:

```bash
docker compose -f infra/docker/docker-compose.yml ps
```

You should eventually see 9 rows, each showing `Up` (some will show
`Up (healthy)` once their health checks pass).

### What you've achieved

You now have the entire platform running:

- **PostgreSQL** is up and has created an empty `agentforge` database
- **Redis** is up, ready to cache LLM responses
- **API Gateway** (port 8000) is listening for HTTP requests
- **Agent Runtime** (port 8001) is ready to execute agent reasoning loops
- **Eval Service** (port 8002) is ready to run test suites
- **Trace Collector** (port 8003) is ready to receive trace data
- **Prometheus** (port 9090) has started scraping metrics from all 4 services
- **Grafana** (port 3000) has auto-loaded its dashboard definitions
- **Dashboard** (port 3001) is serving the React web UI

All of these containers are talking to each other over a private Docker
network — for example, when the API Gateway needs to reach the Agent
Runtime, it uses the hostname `agent-runtime` (the container's name), not
`localhost`. This is exactly how it would work in a real Kubernetes cluster
too, just at a smaller scale.

---

## Step 4: Verify Every Service Is Actually Healthy

### What to do

**If you're using PowerShell** (the default on Windows), note that `curl` is
actually an alias for `Invoke-WebRequest`, which — unlike real curl — requires
the full URL including `http://`. Run:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8002/health
Invoke-RestMethod http://localhost:8003/health
```

`Invoke-RestMethod` is used here instead of `curl`/`Invoke-WebRequest`
because it automatically parses the JSON response and prints it cleanly,
rather than dumping a raw HTTP response object. If you'd rather stick with
`curl`-style syntax, it also works as long as you include the scheme:

```powershell
curl http://localhost:8000/health
```

**If you're using Bash/Git Bash/macOS/Linux**, real `curl` works exactly as
written, scheme optional:

```bash
curl localhost:8000/health
curl localhost:8001/health
curl localhost:8002/health
curl localhost:8003/health
```

Each one should return:

```json
{"status": "ok"}
```

If any of them fail (connection refused, or no response), check that
container's logs:

```bash
docker compose -f infra/docker/docker-compose.yml logs <service-name>
```

(replace `<service-name>` with `api-gateway`, `agent-runtime`,
`eval-service`, or `trace-collector`)

### What you've achieved

You've confirmed that every backend service is not just "running" (a
container can be "running" while its application inside has crashed) but
**actually responding correctly to HTTP requests**. This matters because
Docker's own health check only tells you the process didn't exit — hitting
`/health` yourself confirms the FastAPI application inside is actually
serving traffic.

---

## Step 5: Set Up the Database Schema and Seed Sample Data

### What to do

First, install the Python dependencies for the whole monorepo:

```bash
uv sync --all-packages
```

Then run the seed script:

```bash
uv run python scripts/seed.py
```

This script does two things:
1. Runs against the same PostgreSQL database the containers are using
   (connecting via `localhost:5432`, since the port is published to your
   host machine)
2. Inserts sample data: one demo agent (`demo-support-agent`, using
   `gpt-4o-mini`, with two tools — `search_web` and `get_weather` — and a
   safety policy that blocks PII), a sample run, a sample eval suite with
   test cases, and one API key

When it finishes, it prints something like:

```
Dev API key (save this, shown only once): afk_XXXXXXXXXXXXXXXXXXXXXXXXXX
```

**Copy this key somewhere** — you'll need it for every API call and to log
into the dashboard. It is hashed (SHA-256) before being stored in the
database, so this is the only moment you'll ever see the raw value — exactly
how a real production system should handle secrets.

### What you've achieved

You went from "an empty database with the right table structure" to "a
database with real data you can actually interact with." Specifically:

- **`uv sync --all-packages`** resolved and installed every Python
  dependency across all 6 packages in the monorepo (4 services + 2 shared
  libraries) into one consistent virtual environment, using the lockfile
  (`uv.lock`) to guarantee everyone gets the exact same versions
- **`scripts/seed.py`** gave you a working agent to experiment with instead
  of having to hand-craft a `POST /api/v1/agents` request yourself as your
  very first action, and gave you the authentication key needed to talk to
  the API at all

---

## Step 6: Open the Dashboard in Your Browser

### What to do

Open your browser to:

```
http://localhost:3001
```

You'll see a login gate. Paste the dev API key you copied in Step 5, and
you're in.

### What you've achieved

You're now looking at the same web UI a real user of this platform would
use — no terminal required from this point forward. You can browse to:

- **Agent Catalog** — see `demo-support-agent` listed, with its model and
  tool count
- **Agent Detail** — click into it to see the full system prompt, safety
  policy, and configuration
- **Settings** — see your current API key and session info

This confirms the full request chain works end-to-end: browser → Dashboard
(React, port 3001) → API Gateway (port 8000) → PostgreSQL, and that CORS is
configured correctly to let the dashboard's origin talk to the gateway.

---

## Step 7: Run an Agent for Real (Optional — Costs a Fraction of a Cent)

### What to do

**Option A — via the Dashboard**: Click into `demo-support-agent`, type a
message like *"What's the weather in San Francisco?"* into the message box,
and click Run.

**Option B — via curl/PowerShell**:

In PowerShell:

```powershell
$env:KEY = "afk_..."   # your dev key from Step 5

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/agents/<agent-id>/run" `
  -Headers @{ "X-API-Key" = $env:KEY } `
  -ContentType "application/json" `
  -Body '{"input": "What time is it right now?"}'
```

(The backtick `` ` `` at the end of a line is PowerShell's line-continuation
character — equivalent to bash's `\`.)

In Bash/Git Bash:

```bash
export KEY=afk_...   # your dev key from Step 5

curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"input": "What time is it right now?"}' \
  http://localhost:8000/api/v1/agents/<agent-id>/run
```

(You can get `<agent-id>` from `GET /api/v1/agents` with the same key, or
just use the Dashboard, which fills this in for you automatically.)

### What you've achieved

This is the moment the **entire platform actually does its core job**. Here
is exactly what happened behind the scenes, step by step:

1. The **API Gateway** authenticated your key (hashed lookup against the
   `api_keys` table), loaded the agent's config from Postgres, checked
   today's spend against any daily budget limit, and created a `Run` record
   with status `pending`
2. It forwarded the request over HTTP to the **Agent Runtime**
3. The Agent Runtime called **LiteLLM**, which routed the call to OpenAI
   using your BYOK key from `.env`
4. If the model decided it needed a tool (like `get_current_time`), the
   Agent Runtime executed that tool in Python and fed the result back into
   the conversation, then called the LLM again — this is the "think → act →
   observe" loop
5. **Safety checks** ran automatically after the LLM's response and before
   any tool call, scanning for PII patterns and blocked keywords
6. **OpenTelemetry spans** were emitted for every step (LLM call, tool call,
   safety check), each with timing and token counts
7. The Agent Runtime returned the final answer to the API Gateway, which
   persisted `RunStep` rows (one per step) and a `CostRecord` (real dollar
   cost, calculated from actual token counts) to Postgres, then marked the
   `Run` as `completed`

You've just exercised the full "agent-native" value proposition of this
platform in one request: execution, tool use, safety enforcement, cost
tracking, and tracing, all happening automatically around a single LLM call.

---

## Step 8: View the Trace of What Just Happened

### What to do

In the Dashboard, click on the run you just created (under "Recent Runs" on
the agent's detail page), then open its trace.

Or via API:

```powershell
Invoke-RestMethod -Headers @{ "X-API-Key" = $env:KEY } `
  -Uri "http://localhost:8000/api/v1/runs/<run-id>/trace"
```

```bash
curl -H "X-API-Key: $KEY" http://localhost:8000/api/v1/runs/<run-id>/trace
```

### What you've achieved

You're seeing the exact ordered timeline of everything that happened during
that run — each LLM call, each tool call, each safety check, with real
latency and token numbers. This is the feature that makes AgentForge
"agent-native" instead of a simple LLM logging tool: most LLM-ops products
show you one request/response pair, but you're looking at the *entire
reasoning process* the agent went through to arrive at its answer.

---

## Step 9: Check the Monitoring Dashboards

### What to do

Open Grafana:

```
http://localhost:3000
```

Log in with username `admin`, password `agentforge` (as set in
`docker-compose.yml`). Open the **AgentForge** dashboard from the sidebar.

Also check Prometheus directly:

```
http://localhost:9090
```

Under **Status → Targets**, confirm all 4 services show as `UP`.

### What you've achieved

You're now looking at real-time operational metrics for the platform: total
LLM calls, cumulative cost, request latency percentiles, cache hit rate,
safety violations, and more — the same kind of dashboard an on-call engineer
would watch in production. Every panel is backed by real numbers scraped
from the `/metrics` endpoint on each of your 4 running services, not sample
or fake data.

---

## Step 10: Try the Evaluation Pipeline (Optional)

### What to do

The seed script already created a sample eval suite. Run it:

```powershell
Invoke-RestMethod -Method Post -Headers @{ "X-API-Key" = $env:KEY } `
  -Uri "http://localhost:8000/api/v1/eval-suites/<suite-id>/run"
```

```bash
curl -X POST -H "X-API-Key: $KEY" \
  http://localhost:8000/api/v1/eval-suites/<suite-id>/run
```

Then check the results:

```powershell
Invoke-RestMethod -Headers @{ "X-API-Key" = $env:KEY } `
  -Uri "http://localhost:8000/api/v1/eval-runs/<eval-run-id>"
```

```bash
curl -H "X-API-Key: $KEY" http://localhost:8000/api/v1/eval-runs/<eval-run-id>
```

Or browse to the **Evals** page in the Dashboard.

### What you've achieved

You just ran an automated regression test against your agent: the eval
service executed each test case through the Agent Runtime (a real LLM call
per case), scored the results using LLM-as-judge accuracy scoring and tool-
call correctness checking, and gave you back a pass rate, average latency,
and total cost for the whole suite. This is the mechanism that would catch
"I changed a prompt and it got worse" before it reached real users.

---

## Step 11: Explore the Interactive API Docs (Optional)

### What to do

Open:

```
http://localhost:8000/docs
```

### What you've achieved

FastAPI has auto-generated a full interactive Swagger UI from the actual
Pydantic models in the code — every endpoint, every request/response shape,
documented and testable directly in the browser (click "Try it out" on any
endpoint, paste your API key into the auth field at the top, and send real
requests without writing any curl commands). This documentation can never go
stale relative to the code, because it's generated from the same models the
code actually validates against.

---

## Step 12: Shut Everything Down (When You're Done)

### What to do

To stop the containers but keep your data (Postgres volume, etc.):

```bash
docker compose -f infra/docker/docker-compose.yml stop
```

To stop **and delete all data** (start completely fresh next time):

```bash
docker compose -f infra/docker/docker-compose.yml down -v
```

Or use the provided script, which asks for confirmation first:

```bash
scripts/teardown-local.sh
```

### What you've achieved

You've freed up your laptop's CPU/RAM (9 containers do use noticeable
resources) without losing any code — only the running containers stop, the
actual project files are untouched. `down -v` additionally deletes the named
Docker volumes (`postgres_data`, `prometheus_data`, `grafana_data`), which is
useful if you want to test the seed process from a truly empty database
again.

---

## Quick Reference: Every URL You Now Have Access To

| What | URL | Needs Auth? |
|---|---|---|
| Dashboard | http://localhost:3001 | X-API-Key (pasted once at login) |
| API Gateway root/docs | http://localhost:8000/docs | No (docs page itself is public) |
| API Gateway health | http://localhost:8000/health | No |
| Grafana | http://localhost:3000 | admin / agentforge |
| Prometheus | http://localhost:9090 | No |
| Agent Runtime (internal) | http://localhost:8001/health | No, but not meant for direct use |
| Eval Service (internal) | http://localhost:8002/health | No, but not meant for direct use |
| Trace Collector (internal) | http://localhost:8003/health | No, but not meant for direct use |

---

## Troubleshooting — Real Problems This Project Actually Hit

These aren't hypothetical — every one of these was encountered and fixed
during the actual development of this project (documented in full in
`MILESTONES.md`).

| Symptom | Cause | Fix |
|---|---|---|
| Run fails with `400: No LLM API key configured` | `.env`'s `OPENAI_API_KEY` never reached the container because Docker Compose was started without `--env-file .env` | Always run `docker compose -f infra/docker/docker-compose.yml --env-file .env up -d` explicitly — never a bare `up -d` |
| Dashboard container crashes on start with `npm error EJSONPARSE` | A stale/corrupted Docker build cache layer | `docker compose build --no-cache dashboard`, then start again |
| `agent-runtime` never receives a request, run just fails silently | After restarting Docker Desktop, only `api-gateway` and its direct Compose dependencies (Postgres, Redis) came back up — `agent-runtime` stayed stopped because it's only linked via an HTTP call, not a Compose `depends_on` | Always bring up the **whole** stack with a bare `docker compose up -d` (no service name argument) rather than starting one service at a time |
| Integration tests fail only when run all together, not individually | A `sys.path` manipulation in one test file shadowed another module | Not something you'll hit running the app locally — only relevant if you're developing/running the test suite |
| Port already in use | Something else on your machine is using 8000/8001/8002/8003/3000/3001/5432/6379/9090 | Stop the conflicting process, or edit the port mapping (the left side of `"8000:8000"`) in `docker-compose.yml` |

---

## What You've Built, End to End

If you've completed all the steps above, you have personally exercised
every major subsystem of AgentForge:

- ✅ Infrastructure orchestration (Docker Compose bringing up 9 coordinated services)
- ✅ Database schema + seed data (PostgreSQL, Alembic-migrated schema)
- ✅ Authentication (hashed API key lookup)
- ✅ The core agent execution loop (LLM call → tool call → LLM call)
- ✅ Token optimization (LiteLLM routing/caching under the hood)
- ✅ Safety enforcement (in-process PII/keyword checks)
- ✅ Full observability (OpenTelemetry traces + Prometheus metrics + Grafana dashboards)
- ✅ The evaluation pipeline (automated test suite scoring)
- ✅ A complete web dashboard (React UI talking to the same API you can curl directly)

This is the same verification discipline the project itself was built with —
every milestone in `MILESTONES.md` was confirmed by actually running the
system this way, not just by reading the code.

---

*For a much deeper explanation of every design decision, tool choice, and
difficulty encountered while building this platform, see
[`docs/PROJECT_DOSSIER.md`](PROJECT_DOSSIER.md).*
