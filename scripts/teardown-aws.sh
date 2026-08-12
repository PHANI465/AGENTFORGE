#!/usr/bin/env bash
# Destroys every AWS resource for a given environment (VPC, EKS, RDS,
# ElastiCache, ECR, S3) via Terraform. This is the counterpart to
# terraform apply -var-file=envs/<env>.tfvars and exists specifically so
# nothing gets left running and billing after a demo — see
# docs/aws-cost-estimate.md for what "left running" costs per day.
#
# Usage: scripts/teardown-aws.sh <dev|staging|prod>
set -euo pipefail

ENVIRONMENT="${1:-}"
if [[ -z "$ENVIRONMENT" ]]; then
  echo "Usage: $0 <dev|staging|prod>"
  exit 1
fi
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "prod" ]]; then
  echo "environment must be one of: dev, staging, prod (got: $ENVIRONMENT)"
  exit 1
fi

cd "$(dirname "$0")/../infra/terraform"

if [[ "$ENVIRONMENT" == "prod" ]]; then
  echo "!! You are about to destroy the PRODUCTION AWS environment !!"
  read -r -p "Type the environment name to confirm ('prod'): " confirm
  if [[ "$confirm" != "prod" ]]; then
    echo "Aborted."
    exit 1
  fi
fi

echo "Planning destroy for environment: $ENVIRONMENT"
terraform init -input=false
terraform plan -destroy -var-file="envs/${ENVIRONMENT}.tfvars" -out=destroy.tfplan

read -r -p "Review the plan above. Apply destroy? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted. No changes made."
  rm -f destroy.tfplan
  exit 1
fi

terraform apply destroy.tfplan
rm -f destroy.tfplan

echo "Done. Load balancers/EIPs created by Kubernetes Ingress or Service"
echo "controllers (not Terraform) can outlive the cluster — double check:"
echo "  aws elbv2 describe-load-balancers --region us-east-1"
echo "  aws ec2 describe-addresses --region us-east-1"
