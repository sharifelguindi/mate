variable "tenant_name" {
  description = "Name of the tenant"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, production)"
  type        = string
}

variable "admin_username" {
  description = "Username for the admin user"
  type        = string
  default     = "admin"
}

variable "admin_email" {
  description = "Email address for the admin user"
  type        = string
}

variable "create_admin_user" {
  description = "Whether to create an initial admin user"
  type        = bool
  default     = true
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}