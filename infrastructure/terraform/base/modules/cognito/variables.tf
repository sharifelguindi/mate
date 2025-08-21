variable "environment" {
  description = "Environment name"
  type        = string
}

variable "kms_key_id" {
  description = "KMS key ID for encryption"
  type        = string
}

variable "domain" {
  description = "Cognito domain prefix"
  type        = string
}
