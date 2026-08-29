variable "domain_name" {
  description = "Domain (or subdomain) this environment is served from, e.g. \"agentforge.example.com\". A placeholder until a real domain is owned — see docs/deployment-runbook.md."
  type        = string
}

variable "create_zone" {
  description = "true: create a new hosted zone for domain_name (first environment to use this domain). false: look up an existing zone by name instead (e.g. staging/prod sharing a zone dev already created)."
  type        = bool
  default     = true
}
