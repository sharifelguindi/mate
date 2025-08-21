variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "domain_name" {
  description = "Base domain name for the application"
  type        = string
}

variable "create_route53_zone" {
  description = "Whether to create a new Route53 hosted zone"
  type        = bool
  default     = false
}

variable "cognito_domain" {
  description = "Domain prefix for Cognito hosted UI"
  type        = string
}

variable "cost_center" {
  description = "Cost center for billing tags"
  type        = string
  default     = "engineering"
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for RDS and other resources"
  type        = bool
  default     = true
}

variable "route53_zone_id" {
  description = "Route53 hosted zone ID (if already exists)"
  type        = string
  default     = ""
}

variable "tenants" {
  description = "Map of tenant configurations"
  type        = map(any)
  default     = {}
}
