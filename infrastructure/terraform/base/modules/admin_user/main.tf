# Module for creating initial admin users for tenants

resource "random_password" "admin_password" {
  length  = 16
  special = true
  upper   = true
  lower   = true
  numeric = true
}

# Store admin credentials in AWS Secrets Manager
resource "aws_secretsmanager_secret" "admin_credentials" {
  name        = "${var.tenant_name}-admin-credentials-${var.environment}"
  description = "Initial admin credentials for ${var.tenant_name}"

  tags = {
    Tenant      = var.tenant_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_secretsmanager_secret_version" "admin_credentials" {
  secret_id = aws_secretsmanager_secret.admin_credentials.id
  secret_string = jsonencode({
    username              = var.admin_username
    email                = var.admin_email
    password             = random_password.admin_password.result
    force_password_change = true
    created_at           = timestamp()
  })
}

# Null resource to trigger admin user creation via ECS task
resource "null_resource" "create_admin_user" {
  # Only create if this is a new deployment
  count = var.create_admin_user ? 1 : 0

  triggers = {
    tenant_name    = var.tenant_name
    admin_username = var.admin_username
    admin_email    = var.admin_email
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Admin user credentials stored in AWS Secrets Manager"
      echo "Secret Name: ${aws_secretsmanager_secret.admin_credentials.name}"
      echo ""
      echo "To retrieve credentials:"
      echo "aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.admin_credentials.name} --region ${var.aws_region}"
      echo ""
      echo "To create the user in Django, run:"
      echo "just create-admin ${var.admin_username} ${var.admin_email}"
    EOT
  }
}

# Output the secret ARN for use in ECS task definitions
output "admin_secret_arn" {
  value       = aws_secretsmanager_secret.admin_credentials.arn
  description = "ARN of the secret containing admin credentials"
}

output "admin_secret_name" {
  value       = aws_secretsmanager_secret.admin_credentials.name
  description = "Name of the secret containing admin credentials"
}

output "retrieve_command" {
  value = "aws secretsmanager get-secret-value --secret-id ${aws_secretsmanager_secret.admin_credentials.name} --region ${var.aws_region}"
  description = "Command to retrieve admin credentials"
}
