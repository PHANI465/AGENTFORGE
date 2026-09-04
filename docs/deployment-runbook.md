# Deployment Runbook — Going Live on Real AWS/Kubernetes

This is the step-by-step for turning the validated-but-never-applied
Terraform/Helm into a real, publicly reachable HTTPS URL. See
[`ADR-005`](../CLAUDE.md#adr-005-real-awsk8s-deployment-is-opt-in-not-the-default)
for why this is a deliberate, gated, one-environment-at-a-time process
rather than something that happens automatically on push.

Nothing here is required to run AgentForge locally — `make dev` /
`docker compose up` (Docker Compose, $0) covers that on its own. This
runbook is only for the "someone else can actually visit a URL" step.

## No domain yet? Skip straight to a public demo URL

You don't need a domain, ACM, Route53, or the `auth-service` to get a
real public URL — `enable_ingress = true` alone provisions everything a
bare `http://<alb-hostname>` needs, and `values-staging.yaml` is already
shaped for exactly this (no TLS, `auth-service.enabled: false`, WAF on).
This is the cheapest path to "anyone can visit a link and try the demo":

1. Skip prerequisite 1 below (no domain needed) and prerequisite 3's
   auth-service secrets (the service isn't deployed in this mode).
2. In `envs/staging.tfvars` (copied from the tracked `.example`), leave
   `enable_ingress = true` and `enable_tls = false` — this is already the
   checked-in default.
3. Follow Steps 1–4 below as written; skip the `ACM_CERTIFICATE_ARN` /
   `EXTERNAL_DNS_ROLE_ARN` secrets and the `route53_name_servers` /
   domain-delegation part of Step 1.5 — nothing produces them when
   `enable_tls = false`.
4. In Step 3, `kubectl get ingress` prints the ALB's own hostname (e.g.
   `k8s-agentforge-....elb.amazonaws.com`) in the `ADDRESS` column — that
   *is* your public demo URL, `http://` only (no cert to serve HTTPS).
5. Still spin up → demo → tear down (Step 4) rather than leaving it
   running, same cost reasoning as everywhere else in this runbook.

Turn on a real domain + HTTPS + auth-service later by following the
rest of this runbook once you own one — nothing above needs to be undone
to do that; `enable_tls` and `auth-service.enabled` just get flipped on
top of what's already live.

## Bootstrapping state for a new environment (once per environment, before Step 1)

Terraform's own state for this project lives in an S3 bucket + DynamoDB
lock table (`modules/s3`), one pair per environment — but that bucket has
to exist before the S3 backend (`versions.tf`) can be initialized against
it, which is a real chicken-and-egg problem the first time any given
environment (`dev`, `staging`, `prod`) is ever applied. Skip this section
entirely for an environment that's already been bootstrapped once.

1. In that environment's `envs/<env>.tfvars`, set `create_state_bucket =
   true`.
2. Run **Actions → Infra Apply → Run workflow** with `bootstrap_state`
   checked (plan first, then apply, same review pattern as normal). This
   creates *only* the S3 bucket + DynamoDB table (`-target=module.s3`),
   using local, throwaway state (`-backend=false`) — there's nothing to
   persist yet since the backend it would persist to doesn't exist until
   this step finishes.
3. Set `create_state_bucket` back to `false` in that environment's
   `tfvars`. This matters: left `true`, the *next* normal apply would try
   to create a bucket that already exists and fail. The bucket becomes an
   out-of-band backend target from here on — not a resource this state
   tracks — which is intentional and fine to leave as-is.
4. From here on, run Infra Apply normally (`bootstrap_state` unchecked).
   `terraform init` now configures the real S3 backend, and state
   persists across every future CI run for that environment — no more
   losing track of what a partially-failed apply already created.

If you ever hit a failed apply against an environment that skipped this
(state was local-only, now lost, and AWS may hold orphaned resources from
whatever succeeded before the failure): reconcile or delete those
resources by hand first, *then* bootstrap state before retrying — don't
bootstrap on top of an unknown, possibly-inconsistent set of existing
resources.

## Prerequisites (once, before any environment goes live)

0. **`envs/*.tfvars` is gitignored** (same pattern as `.env`) — the
   tracked reference is `envs/<env>.tfvars.example`, which is a complete,
   working config on its own (nothing sensitive in it; `db_password` comes
   from `TF_VAR_db_password`/the `DB_PASSWORD` secret, never a file).
   `infra-apply.yml` runs against the `.example` file directly, since
   that's what actually exists in a CI checkout. If you're applying from
   your own machine instead, `cp envs/<env>.tfvars.example envs/<env>.tfvars`
   and edit the copy — either way, edit whichever file you're actually
   going to apply with.
1. **A domain you own.** `enable_tls` defaults to `false` and every
   `envs/*.tfvars.example` ships with a placeholder domain
   (`staging.agentforge.example.com` / `agentforge.example.com`) — replace
   `agentforge.example.com` with a real domain (see prerequisite 0 for
   which file to edit), and in the matching
   `infra/helm/agentforge/values-<env>.yaml`'s `ingress.host`. Both must
   match exactly.
2. **AWS OIDC role for CI** (`AWS_DEPLOY_ROLE_ARN` secret) — see the
   existing `infra/terraform/modules/eks`'s OIDC provider; this project
   already avoids static AWS keys everywhere, including here.
3. **`DB_PASSWORD` and `ENCRYPTION_MASTER_KEY` repo secrets** — the former
   feeds `TF_VAR_db_password`; the latter is a real, generated key
   (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
   — never reuse the throwaway value from CI's test job.
4. **GitHub Environment gates**: create `infra-dev` / `infra-staging` /
   `infra-prod` under Settings → Environments, with "Required reviewers"
   set to yourself. This is what makes `infra-apply.yml`'s `apply` job
   actually pause for confirmation instead of firing immediately.

## Step 1 — Provision infrastructure

1. Set `enable_tls = true` in the target environment's `envs/<env>.tfvars`
   (it ships `false`). For a public demo environment (see
   `docs/PROJECT_DOSSIER.md`'s ecosystem section), also set `enable_waf =
   true` — rate-limiting + AWS's managed common rule set in front of
   whatever's public.
2. Run **Actions → Infra Apply → Run workflow**, choosing the environment,
   leaving "apply" unchecked first — this runs `terraform plan` only and
   uploads the plan as a build artifact. Read it.
3. Re-run with "apply" checked. The `apply` job pauses for the
   environment's required-reviewer approval (see prerequisite 4) before
   actually running `terraform apply`.
4. Once it completes, the job prints `terraform output` — copy these into
   repo secrets for `cd.yml` to use:
   - `acm_certificate_arn` → `ACM_CERTIFICATE_ARN`
   - `lb_controller_irsa_role_arn` → `LB_CONTROLLER_ROLE_ARN`
   - `external_dns_irsa_role_arn` → `EXTERNAL_DNS_ROLE_ARN`
   - `waf_web_acl_arn` → `WAF_WEB_ACL_ARN` (only set if `enable_waf = true`)
   - `vpc_id` → `VPC_ID` — always set this alongside `LB_CONTROLLER_ROLE_ARN`.
     Without it the controller falls back to discovering its VPC via EC2
     instance metadata from inside its own pod, which fails outright
     (`CrashLoopBackOff`, "failed to fetch VPC ID from instance metadata")
     unless the node group's metadata hop limit is separately raised to 2.
5. **If `create_route53_zone = true`** (the default), `terraform output
   route53_name_servers` prints the NS records Route53 assigned. Add
   those as NS records at your domain registrar — until you do, the
   zone exists in AWS but the domain doesn't actually point at it, and
   the ACM DNS validation record (which Terraform already created) won't
   be resolvable, so `terraform apply` will hang waiting for certificate
   validation. Delegate the domain **before** running apply if you can;
   if you can't, expect the apply to time out on `aws_acm_certificate_validation`
   until you delegate it and re-run.

## Step 2 — Deploy the application

1. Set the repository variable `DEPLOY_TO_AWS = true` and
   `DEPLOY_ENVIRONMENT = <dev|staging|prod>` (Settings → Variables).
2. Push to `main`, or manually run the **CD** workflow. `deploy-eks`:
   - installs/upgrades the AWS Load Balancer Controller (skipped if
     `LB_CONTROLLER_ROLE_ARN` isn't set — i.e. a no-op until Step 1 ran)
   - installs/upgrades `external-dns` (same skip condition)
   - runs `helm upgrade --install agentforge` with the ACM cert ARN and
     all the app secrets

## Step 3 — Verify

```bash
aws eks update-kubeconfig --region <region> --name agentforge-<env>
kubectl get ingress                       # ADDRESS column should show an ALB hostname
kubectl get pods -n kube-system | grep -E 'load-balancer|external-dns'
curl -I https://<your-domain>              # expect 200, and a real cert (not self-signed)
```

DNS propagation (external-dns picking up the Ingress and creating the
Route53 record) can take a few minutes on first deploy.

## Step 4 — Tear down

**From GitHub (no local tools needed):** run **Actions → Infra Apply →
Run workflow** with **destroy** checked and apply unchecked first to
review what gets removed, then re-run with **destroy and apply** both
checked. Before Terraform destroys the cluster, a pre-destroy step
uninstalls the app + Load Balancer Controller so the ALB — which the
controller creates and which is **not** in Terraform state — is torn
down cleanly (the Ingress finalizer blocks until the ALB is actually
gone) rather than left orphaned and billing. The S3 state bucket/lock
table are deliberately kept, so you can re-apply the environment later
without re-bootstrapping.

**From your own machine (needs Terraform + AWS CLI):**

```bash
scripts/teardown-aws.sh <dev|staging|prod>
```

Either way, the ALB cleanup is best-effort. If the cluster was already
unreachable when teardown ran (so the pre-destroy step was skipped),
any ALB/target-group/EIP created by the Load Balancer Controller is
**not** in Terraform's state — check `aws elbv2 describe-load-balancers`
and `aws ec2 describe-addresses` afterward and remove anything orphaned
by hand.

See [`docs/aws-cost-estimate.md`](aws-cost-estimate.md) for what each
environment costs per hour if left running — the intended pattern is
still spin-up → demo → tear down, not always-on hosting.
