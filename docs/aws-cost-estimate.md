# AWS Cost Estimate

> Per ADR-003 (`CLAUDE.md`), AgentForge runs entirely on Docker Compose locally at
> **$0**. Everything in `infra/terraform/` and `infra/helm/` is production-ready
> configuration that is **not required to run the platform** — it exists to prove
> the infrastructure is real and deployable, not because the project needs a live
> AWS account. This document estimates what actually applying it would cost.

All figures are **approximate on-demand `us-east-1` pricing**, rounded to the
nearest dollar. AWS pricing changes over time and varies by region — treat this
as a planning estimate, not a quote. For an exact number, use the
[AWS Pricing Calculator](https://calculator.aws) with the instance types below,
or `aws ce get-cost-and-usage` against a real account.

## What's actually billed

Every environment (`envs/{dev,staging,prod}.tfvars`) provisions the same
categories of resource, just sized differently:

| Resource | Billed by | Notes |
|---|---|---|
| EKS control plane | flat hourly rate, per cluster | Same cost regardless of node count |
| EC2 worker nodes (EKS node group) | hourly, per instance | `eks_node_instance_types` × `eks_node_desired_size` |
| NAT Gateway(s) | hourly + per-GB data processed | `single_nat_gateway=true` uses one shared gateway instead of one per AZ |
| RDS (Postgres) | hourly (instance) + per-GB-month (storage) | Multi-AZ roughly doubles the instance cost |
| ElastiCache (Redis) | hourly, per node | `redis_num_cache_nodes` × node type |
| Application Load Balancer | hourly + LCU (load balancer capacity units) | Only when `ingress.enabled=true` (staging/prod) |
| ECR | per-GB-month storage | Negligible at this scale — a handful of images |
| S3 + DynamoDB (Terraform state) | negligible | Only if `create_state_bucket=true` |

## Estimated monthly cost by environment

These assume the environment runs **24/7 for a full month** — see
[Cost of a demo session](#cost-of-a-demo-session-the-realistic-case) below for
what a short-lived spin-up/teardown actually costs, which is the intended usage
pattern (`scripts/teardown-aws.sh`).

### Dev (`envs/dev.tfvars`)

| Line item | Shape | Est. $/month |
|---|---|---|
| EKS control plane | 1 cluster | $73 |
| EC2 nodes | 1× `t3.medium` | $30 |
| NAT Gateway | 1 (shared) | $38 |
| RDS | `db.t4g.micro`, 20GB, single-AZ | $14 |
| ElastiCache | `cache.t4g.micro` × 1 | $12 |
| ECR | ~5 images | $1 |
| **Total** | | **≈ $168/month** |

### Staging (`envs/staging.tfvars`)

| Line item | Shape | Est. $/month |
|---|---|---|
| EKS control plane | 1 cluster | $73 |
| EC2 nodes | 2× `t3.medium` | $60 |
| NAT Gateway | 1 (shared) | $38 |
| RDS | `db.t4g.small`, 50GB, single-AZ | $29 |
| ElastiCache | `cache.t4g.small` × 1 | $23 |
| ALB | ingress enabled | $26 |
| ECR | ~5 images | $1 |
| **Total** | | **≈ $250/month** |

### Prod (`envs/prod.tfvars`)

| Line item | Shape | Est. $/month |
|---|---|---|
| EKS control plane | 1 cluster | $73 |
| EC2 nodes | 3× `t3.large` | $180 |
| NAT Gateways | 3 (one per AZ) | $114 |
| RDS | `db.r6g.large`, 100GB, **Multi-AZ** | $362 |
| ElastiCache | `cache.r6g.large` × 2 | $220 |
| ALB | ingress enabled | $26 |
| ECR | ~5 images | $2 |
| **Total** | | **≈ $980/month** |

The prod jump is dominated by two decisions that are each individually
reasonable in a real production system but expensive here: RDS Multi-AZ
(`rds_multi_az = true`, roughly doubles the RDS line) and one NAT Gateway per
AZ instead of a shared one (`single_nat_gateway = false`, for AZ-failure
resilience). Both are one-line tfvars flips back to the cheaper dev/staging
shape if that tradeoff isn't worth it for a given deployment.

## Cost of a demo session (the realistic case)

The dev environment is meant to be brought up, demonstrated, and torn down —
not left running. At the dev shape's combined **≈ $0.22/hour**:

| Session length | Cost |
|---|---|
| 1 hour (portfolio demo call) | ≈ $0.22 |
| 4 hours (a work session) | ≈ $0.88 |
| 24 hours (forgot to tear down overnight) | ≈ $5.28 |
| 1 week (forgot for real) | ≈ $37 |

This is exactly why `scripts/teardown-aws.sh` exists — `terraform apply` to
prove it works, demo it, then `scripts/teardown-aws.sh dev` before closing the
laptop.

## AWS Free Tier

A new AWS account's 12-month Free Tier covers `db.t2/t3/t4g.micro` RDS and
`cache.t2/t4g.micro` ElastiCache instances (750 hours/month each) and 750
hours/month of `t2.micro`/`t3.micro` EC2 — the dev environment's RDS and Redis
line items would be **$0** under Free Tier, and swapping
`eks_node_instance_types` to `["t3.micro"]` would zero out the node cost too
(though `t3.micro`'s 1GB RAM is tight for 5 services — `t3.small` is a safer
free-tier-adjacent floor). EKS control plane and NAT Gateway are never Free
Tier eligible, so realistically the floor for even a maximally frugal dev spin-up
is close to the **$73 (EKS) + $38 (NAT)** ≈ $111/month if left running, or
about $0.15/hour for a demo session.

## What's not in this estimate

- **Data transfer out to the internet** — negligible for a demo, could matter
  under real traffic.
- **CloudWatch Logs/Metrics** ingestion and retention if enabled beyond what
  EKS/RDS include by default.
- **LLM API costs** — entirely separate and outside AWS billing (ADR-002,
  BYOK — users pay their own OpenAI bill, tracked in-platform via
  `GET /api/v1/analytics/costs`).
