# Data Model

Matches `packages/common/agentforge_common/orm.py` exactly — 9 tables, all
Postgres, all owned by the API Gateway (Agent Runtime, Eval Service, and
Trace Collector are stateless and never write directly to these tables).

```mermaid
erDiagram
    AGENTS ||--o{ AGENT_VERSIONS : "has"
    AGENTS ||--o{ RUNS : "executes as"
    AGENTS ||--o{ EVAL_SUITES : "is tested by"
    AGENTS ||--o{ COST_RECORDS : "accrues"
    RUNS ||--o{ RUN_STEPS : "contains"
    RUNS ||--o{ COST_RECORDS : "may accrue"
    EVAL_SUITES ||--o{ EVAL_RUNS : "run as"
    EVAL_RUNS ||--o{ EVAL_RESULTS : "produces"

    AGENTS {
        uuid id PK
        string name
        string model
        text system_prompt
        jsonb tools_config
        jsonb safety_policy
        jsonb config "TokenOptimizationConfig lives here"
        enum status "draft | active | archived"
        timestamptz created_at
        timestamptz updated_at
    }

    AGENT_VERSIONS {
        uuid id PK
        uuid agent_id FK
        int version
        jsonb snapshot "full config at this version"
        timestamptz created_at
    }

    API_KEYS {
        uuid id PK
        string key_hash UK "hashed, never the raw key"
        string user_id
        string provider "e.g. openai"
        text encrypted_key "BYOK LLM key, ADR-002"
        timestamptz created_at
    }

    RUNS {
        uuid id PK
        uuid agent_id FK
        int agent_version
        text input
        text output
        enum status "pending|running|completed|failed"
        string trace_id "OTel root span id"
        timestamptz started_at
        timestamptz completed_at
    }

    RUN_STEPS {
        uuid id PK
        uuid run_id FK
        int step_number
        enum type "llm_call | tool_call | safety_check"
        jsonb input
        jsonb output
        int tokens_in
        int tokens_out
        int latency_ms
        timestamptz created_at
    }

    EVAL_SUITES {
        uuid id PK
        string name
        uuid agent_id FK
        jsonb test_cases
        timestamptz created_at
    }

    EVAL_RUNS {
        uuid id PK
        uuid suite_id FK
        int agent_version
        enum status "pending|running|completed|failed"
        jsonb summary "pass_rate, avg_latency_ms, total_cost_usd"
        timestamptz started_at
        timestamptz completed_at
    }

    EVAL_RESULTS {
        uuid id PK
        uuid eval_run_id FK
        string test_case_id
        bool passed
        float score
        text actual_output
        int latency_ms
        int tokens_used
        jsonb safety_violations
        timestamptz created_at
    }

    COST_RECORDS {
        uuid id PK
        uuid agent_id FK
        uuid run_id FK "nullable — SET NULL if run deleted"
        string model
        int tokens_in
        int tokens_out
        numeric cost_usd "12,6 precision"
        timestamptz created_at
    }
```

**Notable design choices:**
- `AGENTS.config` and `AGENTS.safety_policy` are JSONB, not normalized tables
  — both are small, always read/written as a whole unit with the agent, and
  change shape between milestones (e.g. `TokenOptimizationConfig` was added
  in Milestone 7 with zero migrations, since it just lives inside existing
  JSONB).
- `RUN_STEPS.type` is a single enum covering three very different kinds of
  step (LLM call, tool call, safety check) rather than three separate tables
  — the Trace Viewer needs to render them as one ordered timeline anyway, and
  a shared `input`/`output` JSONB shape is flexible enough for all three.
- `COST_RECORDS.run_id` is nullable with `ON DELETE SET NULL` — a cost record
  survives its originating run being deleted, since spend history shouldn't
  disappear with the run that generated it.
