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

3. **A CI env var gap had been hiding two real bugs for who knows how long**
   (post-milestone hardening). CI was missing `ENCRYPTION_MASTER_KEY` after
   BYOK encryption shipped, so the full test suite — unit and integration
   together — had never once completed successfully anywhere, in CI or
   locally. Fixing the env var and actually running it end-to-end against a
   real Postgres immediately surfaced two more bugs that every mocked unit
   test had been sailing past: agent deletion always raised `IntegrityError`
   (a SQLAlchemy relationship was nullifying a `NOT NULL` FK column instead
   of trusting the database's own `ON DELETE CASCADE`), and "list recent
   runs" wasn't reliably newest-first (`datetime.now(UTC)` returned the
   identical value across several rapid sequential calls on this dev
   machine, and a single-column sort has no way to break that tie). Neither
   bug touches anything a mock would exercise — a fake DB session doesn't
   enforce foreign keys, and a mocked clock doesn't have resolution limits.

All three are documented with full detail in `MILESTONES.md` — the project
keeps a "bugs caught and fixed" section per milestone specifically so this
kind of thing doesn't get lost.

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
needed. The key is encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256,
see `docs/security.md`), and Gateway-level rate limiting (slowapi, per-key)
complements the per-agent daily budget so both spend and request volume are
bounded.

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

Straight answers, not a sales pitch. BYOK encryption and Gateway rate
limiting used to top this list — both are done now, which is itself worth
mentioning unprompted (naming a gap and then actually closing it in a later
pass is a stronger signal than either alone):
- Streaming responses — SSE + LiteLLM's `stream=True`, so a run doesn't feel
  like a 1-5 second silent wait.
- Multi-provider support — LiteLLM already handles 140+ providers; the
  `api_keys` table would need to support more than one provider key per user.
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
