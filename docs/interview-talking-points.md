# Interview Talking Points

Things worth highlighting about AgentForge in a technical conversation —
organized by the kind of question that tends to surface them.

## "Walk me through the architecture"

Six components, clean boundary: **API Gateway** is the only externally-reachable
service; **Agent Runtime**, **Eval Service**, and **Trace Collector** are
internal-only and fully stateless — no in-memory state survives a request,
all persistence goes through Postgres. That statelessness wasn't incidental:
it's what makes the Helm chart's autoscaling (`infra/helm/agentforge/values.yaml`,
HPAs on `api-gateway` and `agent-runtime`) safe to turn on without session
affinity or sticky routing. See `docs/diagrams/architecture.md`.

## "What was the hardest bug you hit?"

Two good stories, both from *live verification*, not code review:

1. **Cache hits were still being billed** (Milestone 7). The budget-limit
   feature's whole point is capping spend, but `litellm.completion_cost()`
   ran unconditionally regardless of `cache_hit` — a response served free
   from Redis still added its notional token cost to the run total. Caught
   by comparing two identical back-to-back eval runs and noticing the cost
   delta was exactly `$0.00` despite an obvious latency drop — if caching
   were actually saving money, that number should have moved. Good example
   of a bug that's invisible in unit tests (which mock the LLM call) and
   only shows up when you actually run the system twice and compare.

2. **A stale Docker build cache shipped an empty `package.json`** (Milestone 8).
   `docker compose build` reused a corrupted cached layer even though the
   real file on disk was fine — the container crashed on every start with
   `npm error EJSONPARSE`. `docker build --no-cache` fixed it. Neither
   `tsc` nor `vite build` running locally would ever have caught this — the
   failure only exists inside the image build pipeline.

Both are documented with full detail in `MILESTONES.md` — the project keeps
a "bugs caught and fixed" section per milestone specifically so this kind of
thing doesn't get lost.

## "Why LiteLLM instead of building your own LLM proxy?"

ADR-001 in `CLAUDE.md`: LiteLLM already solves routing, caching, and cost
tracking across 140+ providers with 53K+ GitHub stars behind it — building a
custom proxy would be months of work to re-derive something that exists and
is maintained. The judgment call worth defending: know when *not* to build
something. The one place AgentForge does add its own logic on top
(`services/agent-runtime/routing.py`'s complexity heuristic, deciding which
model tier a request goes to) is genuinely platform-specific decision logic
that LiteLLM has no opinion about — that's the right line to draw.

## "How do you handle multi-tenant LLM costs without AgentForge itself paying?"

ADR-002 — BYOK (bring your own key). Users supply their own OpenAI key;
AgentForge tracks spend by counting tokens × published pricing, never
proxies actual billing. Simpler trust model, no payment infrastructure
needed. The honest gap: that key is currently stored in plaintext in
Postgres (see `docs/security.md`) — worth naming unprompted, since noticing
your own gap before someone else points it out is exactly the signal a good
engineer wants to send.

## "How would this actually run in production?"

`infra/terraform/` + `infra/helm/agentforge/` — real Terraform (VPC, EKS,
RDS, ElastiCache, ECR, least-privilege IAM, OIDC — no static AWS keys
anywhere including CI/CD) and a real Helm chart, both validated (Helm lint +
render-and-inspect across all three environments; all 5 Docker images
actually built). None of it is required to run the platform locally — that's
Docker Compose, $0 — but it exists to prove the production path is real, not
hand-waved. `docs/aws-cost-estimate.md` has honest numbers: about $168/month
if the dev environment ran continuously, or 22 cents an hour for the
realistic use case of spinning it up for a demo and tearing it down after
(`scripts/teardown-aws.sh`).

## "What would you do differently, or do next?"

Straight answers, not a sales pitch:
- Encrypt the BYOK key at rest — the single most important thing missing.
- Rate limiting at the Gateway — currently only a $/day budget cap exists,
  no requests/minute throttle.
- The regex-based PII detector (`services/agent-runtime/safety.py`) catches
  structured PII (emails, SSNs, card numbers) but not free-text descriptions
  of sensitive information — a real system would want a proper PII
  classifier, not pattern matching.
- Semantic caching (LiteLLM supports it) instead of exact-match — a rephrased
  version of the same question currently misses the cache entirely.

## "What's the most 'agent-native' (vs. just LLM-ops) part of the design?"

The Trace Viewer traces the *reasoning loop*, not a single API call — every
LLM call, tool call, and safety check inside one run shows up as an ordered
span with timing and token counts (`docs/diagrams/request-flow.md`). Tools
like LangSmith/Humanloop log request/response pairs; AgentForge's `run_steps`
table and OTel instrumentation capture the whole multi-step decision process
an autonomous agent goes through to get to that response. The eval pipeline
follows the same instinct: scoring isn't just "did the text match" — it also
checks whether the agent called the *right tools*, and any safety violation
during a test case is an automatic fail regardless of how good the final
answer looked.
