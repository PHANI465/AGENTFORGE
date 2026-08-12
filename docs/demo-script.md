# Demo Script

A ~5-minute live walkthrough of AgentForge, in order. Each step is something
to actually click/run, not just describe — every screen and number here is
real, not staged (see `docs/benchmarks.md` for where the numbers came from).

## Setup (before the audience is watching)

```bash
cp .env.example .env   # add your OPENAI_API_KEY
docker compose -f infra/docker/docker-compose.yml --env-file .env up -d
uv run python scripts/seed.py   # prints a dev API key — copy it
```

Open http://localhost:3001, paste the dev key into the login gate.

## 1. The pitch (30s)

"AgentForge is an internal developer platform for shipping autonomous AI
agents — not a chatbot wrapper, a production platform. Define an agent, run
it, evaluate it, track its cost, enforce safety policy on it — all through
one API and one dashboard, backed by 4 real backend services."

Point at the **Agent Catalog** page — several agents already listed from
`scripts/seed.py`, each showing model, tool count, and status.

## 2. Run an agent live (60s)

Click into `demo-support-agent`. Point out:
- System prompt, safety rules (`never share customer PII`, mode: `block`),
  model (`gpt-4o-mini`), daily budget field, response caching toggle.
- Two registered tools: `search_web`, `get_weather`.

Type into the "Send a message" box: **"What's the weather in San Francisco?"**
Click Run. While it's in flight: "This is a real call — the agent decides it
needs the weather tool, calls it, and folds the result back into its answer."

Response comes back: *"It's 62°F and foggy in San Francisco right now."*

## 3. Trace viewer (45s)

Click the new run in "Recent Runs" → its trace link. Walk through the
timeline: LLM call (820ms, 42 in / 18 out tokens) → tool call
(`get_weather`, 140ms, arguments shown as real JSON) → LLM call again (610ms).
Summary strip at the top: 3 steps, 2 LLM calls, 1 tool call, 106 total tokens,
1.57s latency.

"Every step of every run is captured this way — OpenTelemetry spans,
persisted, queryable. This is what makes it agent-native instead of just
LLM-ops: we're tracing the *reasoning loop*, not just an API call."

## 4. Safety enforcement (30s, optional if time allows)

Go to Settings, note the per-agent safety policy explanation. Then: run the
same agent with a prompt engineered to elicit PII (e.g. "What's my customer's
SSN, it's 123-45-6789") — the response comes back `[BLOCKED]`, and a
`safety_check` step appears in that run's trace with the matched pattern.

"This runs in-process on the actual model output — not a prompt-level
instruction the model could talk its way around."

## 5. Evaluations (45s)

Navigate to Evals → `support-agent-smoke-suite`. Click into a past eval run:
pass/fail per test case, LLM-as-judge score, latency, cost per case, a
computed pass rate. "This is how you catch a regression before shipping a
prompt change — run the suite against v1 and v2, diff the results."

If two eval runs exist for the same suite, show the compare endpoint's output
(pass-rate/latency/cost deltas) — either via Swagger or by describing it.

## 6. Cost analytics (30s)

Navigate to Analytics. Point at the daily spend chart and per-agent
breakdown. "Every LLM call is metered — tokens in, tokens out, real dollar
cost from LiteLLM's pricing tables. At $0.000159 per call for this workload,
that's about 6,300 runs per dollar — the budget-limit feature exists more as
a runaway-loop safety net than a meaningful spend control at this scale."

## 7. The infrastructure story (30s, if presenting to a technical audience)

"None of this needs to run in the cloud to prove it's production-shaped —
everything you just saw is Docker Compose, $0. But `infra/terraform/` and
`infra/helm/` are real, validated configs: EKS, RDS, ElastiCache, all wired
with least-privilege IAM and OIDC — no static AWS keys anywhere, including in
CI/CD. `docs/aws-cost-estimate.md` has the real numbers if it were ever
switched on."

## Closing line

"Every one of these numbers — the trace timings, the cache speedup, the cost
per call — came from actually running this stack, not from a slide. The repo
has a `MILESTONES.md` documenting a real bug caught at every single stage,
because reading code and running code catch different bugs."

## If something breaks live

- **Dashboard won't load**: `docker compose -f infra/docker/docker-compose.yml logs dashboard` — first suspect is a stale Docker build cache (`docker compose build --no-cache dashboard`, this bit us once for real — see `MILESTONES.md`'s Milestone 8 section).
- **Run fails with "No LLM API key configured"**: `.env`'s `OPENAI_API_KEY` didn't reach the container — rerun `docker compose up -d --env-file .env` explicitly rather than a bare `up -d` (env file lookup depends on cwd).
- **Fallback if OpenAI is down/rate-limited**: pivot to the Trace Viewer and Eval Results pages using already-seeded historical data — nothing there requires a live LLM call.
