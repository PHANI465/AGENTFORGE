# Request Flow: `POST /api/v1/agents/{id}/run`

One agent run, from the API call to the persisted trace. Matches the real
control flow in `services/api-gateway/routers/runs.py` and
`services/agent-runtime/engine.py`.

```mermaid
sequenceDiagram
    actor U as Caller
    participant GW as API Gateway
    participant PG as Postgres
    participant RT as Agent Runtime
    participant LL as LiteLLM
    participant R as Redis
    participant P as LLM Provider

    U->>GW: POST /agents/{id}/run<br/>X-API-Key, {input}
    GW->>GW: authenticate (hash lookup)
    GW->>PG: load agent config
    GW->>PG: check today's spend vs daily_budget_usd
    alt over budget
        GW-->>U: 429 budget_exceeded
    end
    GW->>PG: INSERT Run (status=pending)
    GW->>RT: POST /run<br/>{agent config, input, BYOK key}

    loop until final answer or max_iterations
        RT->>LL: completion(messages, model)
        alt response cached (exact match, 1h TTL)
            LL->>R: GET cache key
            R-->>LL: cached response
        else cache miss
            LL->>P: chat completion
            P-->>LL: response + usage
            LL->>R: SET cache key (ttl=3600)
        end
        RT->>RT: safety check: POST_LLM checkpoint
        alt violation + on_violation=block
            RT-->>RT: mark failed, stop loop
        end
        opt LLM requested a tool call
            RT->>RT: safety check: PRE_TOOL checkpoint
            RT->>RT: execute tool, append result to context
        end
        RT->>RT: emit OTel span (llm_call / tool_call / safety_check)
    end

    RT-->>GW: RunResult {output, steps[], tokens, cost_usd, trace_id}
    GW->>PG: INSERT RunSteps, CostRecord
    GW->>PG: UPDATE Run (status=completed, output, trace_id)
    GW-->>U: 200 {data: Run}

    U->>GW: GET /runs/{id}/trace
    GW->>PG: SELECT run_steps WHERE run_id
    GW-->>U: 200 {spans[], summary}
```

Cache hits (per Milestone 7) are forced to `cost_usd = 0.0` — a cache-served
response still reports token counts for observability, but doesn't count
against the agent's daily budget.
