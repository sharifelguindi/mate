variable "environment" {
  description = "Environment name"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
}

variable "enable_container_insights" {
  description = "Enable Container Insights"
  type        = bool
  default     = false
}
