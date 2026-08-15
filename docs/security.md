# Security Considerations

An honest account of what AgentForge actually does for security today, and
what it deliberately doesn't — written against the real code
(`packages/common/agentforge_common/security.py`, `services/api-gateway/`,
`services/agent-runtime/safety.py`), not the aspirational version. Where the
implementation falls short of what a production system would need, that's
called out explicitly rather than glossed over — this is a learning/portfolio
project, not a system holding real user data at real stakes, and knowing the
gap is more useful than hiding it.

## Authentication

- Every `/api/v1/*` request requires an `X-API-Key` header
  (`services/api-gateway/dependencies.py`).
- Keys are generated as high-entropy random tokens (`secrets.token_urlsafe(32)`,
  prefixed `afk_`), never user-chosen — so they're hashed with a plain SHA-256
  digest for lookup (`agentforge_common/security.py`), not bcrypt/argon2. That
  tradeoff is deliberate and correct here: bcrypt's cost factor defends against
  offline brute-forcing of low-entropy user-chosen secrets (passwords); a
  256-bit random token has no such weakness to defend against, and a fast
  digest is what you want for a per-request auth lookup.
- The raw key is shown exactly once, at generation time
  (`POST /api/v1/api-keys`), and never stored or logged again — only its hash.
- Keys can be revoked (`DELETE /api/v1/api-keys/{id}`) with two guards: a
  caller cannot revoke the key authenticating their own request, and cannot
  revoke the last remaining key — both would lock every caller out with no
  way back in.

## BYOK LLM key storage (ADR-002)

Per ADR-002, users bring their own LLM provider key (`api_keys.encrypted_key`).
This key is encrypted at rest using Fernet symmetric encryption
(AES-128-CBC + HMAC-SHA256, via `cryptography.fernet.Fernet`) — see
`encrypt_key()`/`decrypt_key()` in `agentforge_common/security.py`. The
master key is read from the `ENCRYPTION_MASTER_KEY` env var, generated once
with:
```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
In the Terraform-provisioned environments, this key would come from AWS
Secrets Manager / KMS rather than a plain env var — `infra/terraform/modules/eks`
already provisions the OIDC provider needed for IRSA (IAM Roles for Service
Accounts) so pods can reach KMS without static credentials. That wiring isn't
done yet; the env var is the local/dev-appropriate version of the same idea.
The local dev fallback (`OPENAI_API_KEY` env var) still exists and bypasses
the encrypted column entirely when no BYOK key is registered.

## Safety policy enforcement (Milestone 4)

- Every agent can declare `safety_policy.rules` (PII pattern matching +
  keyword blocklists) and `on_violation` (`block` / `warn` / `log`).
- Enforcement is in-process, inside `services/agent-runtime/safety.py`,
  checked at two points in the execution loop: after every LLM response and
  before every tool call. It cannot be bypassed by prompt content — the check
  runs on the LLM's actual output text/tool arguments, not on anything the
  model can talk its way around.
- Violations are persisted as their own `run_steps` rows (`type=safety_check`)
  — visible in the Trace Viewer, not silently dropped.
- **Limitation**: PII detection is regex-based (email, phone, SSN, credit
  card patterns) — it catches structured PII, not free-text descriptions of
  sensitive information a determined model might produce. This is pattern
  matching, not a PII classifier.

## Network security

- **CORS** is configured with an explicit allowlist
  (`DASHBOARD_ORIGINS` env var, defaults to `localhost:3001`/`localhost:5173`)
  — not `allow_origins=["*"]`. `allow_credentials=True` is paired with that
  explicit list, never a wildcard (browsers reject the credentialed-wildcard
  combination anyway, but it's worth stating the config is correct on
  purpose).
- **Redis has no auth or TLS** — fine for the Docker Compose network
  (services only reachable from other containers on the same bridge network,
  not published beyond `localhost:6379` for local debugging) and for the
  Terraform-provisioned ElastiCache (security-group-scoped to EKS nodes only,
  see `infra/terraform/modules/elasticache`), but would need
  `transit_encryption_enabled = true` + AUTH token before holding anything
  more sensitive than an LLM response cache.
- **Rate limiting** is enforced at the Gateway via `slowapi`
  (`services/api-gateway/rate_limit.py`), keyed by the caller's API key (or
  client IP if unauthenticated). Defaults: 60 requests/minute for general
  endpoints, 10/minute for the expensive LLM-calling routes (`/run` and
  `/eval-suites/{id}/run`), both overridable via `RATE_LIMIT_DEFAULT` /
  `RATE_LIMIT_RUN` env vars. This is separate from and complements the daily
  cost budget (`daily_budget_usd`, Milestone 7), which limits spend, not
  request volume — a client under budget can still be throttled by rate, and
  vice versa.
- Inter-service HTTP (Gateway → Runtime → Eval Service) has no mTLS — all
  traffic stays inside the Kubernetes cluster network / Docker Compose bridge
  network, never crossing a public boundary directly.

## Least privilege in the provisioned infrastructure

- EKS worker nodes get exactly three IAM policies (`AmazonEKSWorkerNodePolicy`,
  `AmazonEKS_CNI_Policy`, `AmazonEC2ContainerRegistryReadOnly`) — no
  broader `AdministratorAccess`-style shortcuts (`infra/terraform/modules/eks`).
- RDS and ElastiCache security groups only allow ingress from the EKS node
  security group, on their respective ports — not `0.0.0.0/0`, and RDS is
  `publicly_accessible = false`.
- CI/CD (`.github/workflows/cd.yml`) uses OIDC role assumption
  (`aws-actions/configure-aws-credentials` with `role-to-assume`) to reach
  AWS — there is no long-lived `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
  secret anywhere in this repository.

## Input validation

- Every request body is a Pydantic model — malformed/wrong-typed input is
  rejected at the FastAPI layer with a 422 before touching any business logic.
- The `calculate` tool (`services/agent-runtime/tools.py`) evaluates
  expressions via Python's `ast` module, walking a restricted node whitelist —
  not `eval()`/`exec()`. An LLM-supplied expression cannot execute arbitrary
  Python through this tool.

## Secrets hygiene in this repo

- `.env` is gitignored; only `.env.example` (no real values) is committed.
- `infra/terraform/envs/*.tfvars` deliberately omit `db_password` — it's
  read from `TF_VAR_db_password`, never checked in.
- `infra/helm/agentforge/values*.yaml` leave `externalConfig.*` empty —
  real Postgres DSN / Redis URL / OpenAI key are passed via `--set-string`
  at deploy time (see the header comment in `values-dev.yaml`), not committed.

## Summary: what would need to change before production

1. Replace regex-based PII detection with a proper classifier (e.g. Microsoft
   Presidio) — the current checks catch structured PII (emails, SSNs,
   card numbers) but not free-text descriptions of sensitive information.
2. Enable Redis AUTH + TLS if ElastiCache ever holds more than a response cache.
3. Add mTLS or a service mesh if inter-service traffic ever crosses a
   less-trusted network boundary than "inside one VPC."
4. Swap SHA-256-hashed API keys for a rotating/short-lived token scheme
   (e.g. JWTs with expiry) if this ever supports multi-tenant, non-developer
   users — keys can be manually revoked today, but don't auto-expire.
5. Move `ENCRYPTION_MASTER_KEY` from a plain env var to AWS Secrets Manager /
   KMS via IRSA in the deployed environments (the OIDC plumbing already
   exists in `infra/terraform/modules/eks`; only the KMS read is missing).

BYOK key encryption and Gateway rate limiting were both on this list and are
now implemented — see the sections above.
