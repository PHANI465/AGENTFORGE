module "vpc" {
  source = "./modules/vpc"

  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  az_count           = var.az_count
  single_nat_gateway = var.single_nat_gateway
}

module "eks" {
  source = "./modules/eks"

  environment          = var.environment
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  public_subnet_ids    = module.vpc.public_subnet_ids
  cluster_version      = var.eks_cluster_version
  node_instance_types  = var.eks_node_instance_types
  node_desired_size    = var.eks_node_desired_size
  node_min_size        = var.eks_node_min_size
  node_max_size        = var.eks_node_max_size
}

module "rds" {
  source = "./modules/rds"

  environment                 = var.environment
  vpc_id                      = module.vpc.vpc_id
  private_subnet_ids          = module.vpc.private_subnet_ids
  eks_node_security_group_id  = module.eks.node_security_group_id
  instance_class               = var.rds_instance_class
  allocated_storage_gb         = var.rds_allocated_storage_gb
  engine_version                = var.rds_engine_version
  multi_az                     = var.rds_multi_az
  db_name                      = var.db_name
  db_username                  = var.db_username
  db_password                  = var.db_password
}

module "elasticache" {
  source = "./modules/elasticache"

  environment                 = var.environment
  vpc_id                      = module.vpc.vpc_id
  private_subnet_ids          = module.vpc.private_subnet_ids
  eks_node_security_group_id  = module.eks.node_security_group_id
  node_type                   = var.redis_node_type
  num_cache_nodes              = var.redis_num_cache_nodes
}

module "ecr" {
  source = "./modules/ecr"

  environment       = var.environment
  repository_names  = var.ecr_repository_names
}

module "s3" {
  source = "./modules/s3"

  environment          = var.environment
  create_state_bucket  = var.create_state_bucket
}

module "route53" {
  source = "./modules/route53"
  count  = var.enable_tls ? 1 : 0

  domain_name = var.domain_name
  create_zone = var.create_route53_zone
}

module "acm" {
  source = "./modules/acm"
  count  = var.enable_tls ? 1 : 0

  domain_name = var.domain_name
  zone_id     = module.route53[0].zone_id
}

module "lb_controller_irsa" {
  source = "./modules/lb-controller-irsa"
  count  = var.enable_ingress ? 1 : 0

  environment        = var.environment
  oidc_provider_arn  = module.eks.oidc_provider_arn
  oidc_provider_url  = module.eks.oidc_provider_url
}

module "external_dns_irsa" {
  source = "./modules/external-dns-irsa"
  count  = var.enable_tls ? 1 : 0

  environment        = var.environment
  oidc_provider_arn  = module.eks.oidc_provider_arn
  oidc_provider_url  = module.eks.oidc_provider_url
}

module "waf" {
  source = "./modules/waf"
  count  = var.enable_waf ? 1 : 0

  environment = var.environment
}
