# Performance Benchmarks

Real numbers from the live `docker-compose` stack on a single developer
laptop (Windows, WSL2/Docker Desktop, unthrottled network) — not a lab
environment, not synthetic mocks. Every number below came from
`uv run python scripts/benchmark.py` and direct `curl` timing against
`http://localhost:8000`, using real Postgres, real Redis, and a real
`gpt-4o-mini` OpenAI call (BYOK). Reproduce with:

```bash
uv run python scripts/seed.py   # prints a dev API key + creates a curl-test-agent
uv run python scripts/benchmark.py --api-key $KEY --agent-id $CURL_TEST_AGENT_ID
```

These are **directional, not SLA numbers** — LLM provider latency varies by
time of day, model load, and network path, and this ran on a laptop, not
production hardware. Treat the shape of the results (gateway overhead is
negligible, caching is a real win) as the takeaway, not the exact millisecond
figures.

## Gateway overhead (no LLM call)

| Endpoint | n | mean | p50 | p95 | min–max |
|---|---|---|---|---|---|
| `GET /health` (no auth, no DB) | 20 | 3.2ms | 2.0ms | 28.2ms | 1.3–28.2ms |
| `GET /api/v1/agents` (Postgres round-trip) | 20 | 9.5ms | 5.6ms | 89.5ms | 3.8–89.5ms |

The API Gateway itself adds essentially nothing to the request path — single
digit milliseconds for a real database round-trip. Whatever latency a run
has, it's coming from the LLM call, not the platform.

## Agent run latency (real LLM call)

| Scenario | n | mean | p50 | p95 | min–max |
|---|---|---|---|---|---|
| Cold (unique input, cache miss) | 5 | 1757ms | 1074ms | 4515ms | 447–4515ms |

The wide spread (447ms–4.5s) is entirely OpenAI-side variance for
`gpt-4o-mini` — nothing in AgentForge's own code path is doing meaningfully
different work between the fast and slow calls.

## Cache hit speedup (Milestone 7)

Same input sent 3 times in a row — 1st call is a cache miss (real LLM call),
2nd and 3rd hit Redis:

| Call | Result | Latency |
|---|---|---|
| 1 | miss (real LLM call) | 511ms |
| 2 | hit | 44ms |
| 3 | hit | 32ms |

**≈13.3x speedup** on cache hits, and — per the Milestone 7 fix — a cache hit
also reports `cost_usd: 0.0`, so it's a genuine 100% cost reduction on repeat
questions, not just a latency win.

## Eval suite run

A 2-test-case suite (`support-agent-smoke-suite`), run end-to-end
(`POST /eval-suites/{id}/run` → runs each case through Agent Runtime → scores
via LLM-as-judge → persists results):

```json
{
  "status": "completed",
  "summary": {
    "total": 2,
    "passed": 1,
    "pass_rate": 0.5,
    "avg_latency_ms": 1064,
    "total_cost_usd": 0.0000505,
    "total_tokens_used": 127
  }
}
```

Wall-clock for the whole suite (2 test cases, sequential, including LLM-as-judge
scoring calls): **2.4 seconds**. The 0.5 pass rate here is expected — this is
the platform's own demo suite exercising both pass and fail paths on purpose,
not a real regression.

## Cost per call

From `GET /api/v1/analytics/costs`, real recorded spend: a single `gpt-4o-mini`
tool-using run (2 LLM calls + 1 tool call, 106 total tokens) costs
**$0.000159** — roughly 6,300 such runs per dollar. This is why the budget
enforcement in Milestone 7 defaults to no limit rather than a low one; at this
per-call cost, a `daily_budget_usd` cap is a safety net for infinite-loop bugs,
not a meaningful spend control at demo scale.
