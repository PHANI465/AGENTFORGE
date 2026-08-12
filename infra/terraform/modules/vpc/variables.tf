variable "environment" {
  description = "Deployment environment name, used in resource naming."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
}

variable "az_count" {
  description = "Number of availability zones to spread subnets across."
  type        = number
}

variable "single_nat_gateway" {
  description = "Use one shared NAT Gateway instead of one per AZ."
  type        = bool
}
