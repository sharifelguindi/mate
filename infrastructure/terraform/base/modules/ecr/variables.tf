variable "environment" {
  description = "Environment name"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
}

variable "repositories" {
  description = "List of repository names to create"
  type        = list(string)
}
