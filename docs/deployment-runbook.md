# Deployment Runbook — Going Live on Real AWS/Kubernetes

This is the step-by-step for turning the validated-but-never-applied
Terraform/Helm into a real, publicly reachable HTTPS URL. See
[`ADR-005`](../CLAUDE.md#adr-005-real-awsk8s-deployment-is-opt-in-not-the-default)
for why this is a deliberate, gated, one-environment-at-a-time process
rather than something that happens automatically on push.

Nothing here is required to run AgentForge locally — `make dev` /
`docker compose up` (Docker Compose, $0) covers that on its own. This
runbook is only for the "someone else can actually visit a URL" step.

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

```bash
scripts/teardown-aws.sh <dev|staging|prod>
```

Runs `terraform destroy` for that environment. As the script itself
warns: any ALB/target-group/EIP created by the Load Balancer Controller
(as opposed to by Terraform directly) is **not** in Terraform's state —
check `aws elbv2 describe-load-balancers` and `aws ec2 describe-addresses`
after tearing down and remove anything orphaned by hand. This matters
more now than it used to, since a real Ingress with a real ALB is the
whole point of this runbook.

See [`docs/aws-cost-estimate.md`](aws-cost-estimate.md) for what each
environment costs per hour if left running — the intended pattern is
still spin-up → demo → tear down, not always-on hosting.
