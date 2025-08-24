#!/bin/bash
# Script to create initial admin user during Terraform provisioning
# This script is called by Terraform's local-exec provisioner

set -e

# Required environment variables from Terraform
ADMIN_USERNAME="${ADMIN_USERNAME}"
ADMIN_EMAIL="${ADMIN_EMAIL}"
TENANT_ID="${TENANT_ID:-}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Optional: Use AWS Secrets Manager to store the password
AWS_REGION="${AWS_REGION:-us-east-1}"
SECRET_NAME="${SECRET_NAME:-mate-${TENANT_ID}-admin-password}"

echo "Creating admin user for tenant: ${TENANT_ID}"

# Generate secure password
PASSWORD=$(openssl rand -base64 16)

# Store password in AWS Secrets Manager (if AWS CLI is available)
if command -v aws &> /dev/null; then
    echo "Storing password in AWS Secrets Manager..."
    aws secretsmanager create-secret \
        --name "${SECRET_NAME}" \
        --description "Initial admin password for ${TENANT_ID}" \
        --secret-string "{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${PASSWORD}\"}" \
        --region "${AWS_REGION}" 2>/dev/null || \
    aws secretsmanager update-secret \
        --secret-id "${SECRET_NAME}" \
        --secret-string "{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${PASSWORD}\"}" \
        --region "${AWS_REGION}"

    echo "Password stored in AWS Secrets Manager: ${SECRET_NAME}"
fi

# Output for Terraform (can be captured as output)
cat <<EOF
{
  "username": "${ADMIN_USERNAME}",
  "email": "${ADMIN_EMAIL}",
  "secret_name": "${SECRET_NAME}",
  "instructions": "Retrieve password from AWS Secrets Manager using: aws secretsmanager get-secret-value --secret-id ${SECRET_NAME}"
}
EOF
