# Admin User Provisioning Module

This module handles the secure creation of initial admin users for MATE tenants.

## Features

- Generates secure random passwords
- Stores credentials in AWS Secrets Manager
- Forces password change on first login
- PHI/HIPAA compliant credential management

## Usage

### 1. Via Terraform (during infrastructure provisioning)

```hcl
module "admin_user" {
  source = "./modules/admin_user"
  
  tenant_name       = "hospital-a"
  environment       = "production"
  admin_username    = "admin"
  admin_email      = "admin@hospital-a.com"
  create_admin_user = true
}
```

### 2. Via Just Command (manual creation)

```bash
# Create admin user locally
just create-admin admin admin@example.com

# Or using Docker directly
docker compose run --rm django python ./manage.py create_tenant_admin \
  --username admin \
  --email admin@example.com \
  --force-password-change
```

### 3. Via ECS Task (for deployed environments)

```bash
aws ecs run-task \
  --cluster mate-production \
  --task-definition mate-django-migrate \
  --overrides '{
    "containerOverrides": [{
      "name": "django",
      "command": [
        "python", "manage.py", "create_tenant_admin",
        "--username", "admin",
        "--email", "admin@example.com",
        "--output-password"
      ]
    }]
  }'
```

## Retrieving Credentials

After Terraform creates the admin user credentials:

```bash
# Get credentials from AWS Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id hospital-a-admin-credentials-production \
  --region us-east-1 \
  --query SecretString \
  --output text | jq .
```

## Security Considerations

1. **Password Storage**: Passwords are never stored in Terraform state
2. **Secrets Manager**: All credentials are stored encrypted in AWS Secrets Manager
3. **Force Password Change**: Users must change password on first login
4. **Audit Trail**: All secret access is logged in CloudTrail
5. **Rotation**: Implement regular password rotation policies

## PHI Compliance

- Initial passwords are temporary and must be changed
- All credentials are encrypted at rest and in transit
- Access to secrets requires IAM permissions
- Audit logging enabled for all credential access

## Example Output

```json
{
  "username": "admin",
  "email": "admin@hospital-a.com",
  "password": "TEMPORARY_PASSWORD",
  "force_password_change": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```