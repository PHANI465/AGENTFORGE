# System Architecture

```mermaid
flowchart TB
    User(["Developer / Dashboard user"])

    subgraph Edge["Edge"]
        Dashboard["Dashboard<br/>React + TS + Tailwind<br/>:3001"]
    end

    subgraph Gateway["API Gateway :8000"]
        GW["FastAPI<br/>auth · CRUD · CORS · budget checks"]
    end

    subgraph Stateless["Stateless execution services"]
        Runtime["Agent Runtime :8001<br/>think→act→observe loop<br/>safety checks · routing · caching"]
        Eval["Eval Service :8002<br/>test runner · LLM-as-judge scoring"]
        Trace["Trace Collector :8003<br/>OTel span ingestion"]
    end

    subgraph Data["Data layer"]
        PG[("PostgreSQL<br/>agents · runs · evals · costs")]
        Redis[("Redis<br/>LiteLLM response cache")]
    end

    subgraph LLM["Token Optimization"]
        LiteLLM["LiteLLM<br/>routing · caching · cost tracking"]
        Lingua["LLMLingua<br/>optional prompt compression"]
    end

    Provider[["LLM Provider<br/>OpenAI (BYOK)"]]

    subgraph Observability["Observability"]
        Prom["Prometheus :9090"]
        Grafana["Grafana :3000"]
    end

    User --> Dashboard
    Dashboard -- "X-API-Key" --> GW
    User -. "curl / SDK" .-> GW

    GW -- "HTTP" --> Runtime
    GW -- "HTTP" --> Eval
    GW --> PG

    Eval -- "HTTP, per test case" --> Runtime
    Runtime --> Trace
    Runtime --> PG
    Runtime -- "cache read/write" --> Redis
    Runtime --> LiteLLM
    Runtime -.-> Lingua
    LiteLLM --> Provider
    Trace --> PG

    GW -. "/metrics" .-> Prom
    Runtime -. "/metrics" .-> Prom
    Eval -. "/metrics" .-> Prom
    Trace -. "/metrics" .-> Prom
    Prom --> Grafana

    style Dashboard fill:#4f46e5,color:#fff
    style GW fill:#0891b2,color:#fff
    style Runtime fill:#0891b2,color:#fff
    style Eval fill:#0891b2,color:#fff
    style Trace fill:#0891b2,color:#fff
    style Provider fill:#f97316,color:#fff
```

**Service boundary rule**: only the API Gateway is reachable from outside the
cluster (plus the Dashboard, which itself only talks to the Gateway). Agent
Runtime, Eval Service, and Trace Collector are internal-only and stateless —
all persistence goes through Postgres, all inter-service calls are plain HTTP.
This is the same boundary enforced in `infra/helm/agentforge/values.yaml`
(only `api-gateway` and `dashboard` get an `ingressPath`).
