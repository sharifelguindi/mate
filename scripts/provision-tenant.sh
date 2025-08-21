#!/bin/bash
# Script to provision a new tenant in the MATE platform

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to generate random string
generate_random_string() {
    local length=$1
    openssl rand -hex $length | head -c $length
}

# Function to create tenant configuration
create_tenant_config() {
    local tenant_name=$1
    local display_name=$2
    local tier=$3
    local contact_email=$4

    print_message "$YELLOW" "Creating Terraform configuration for tenant: $tenant_name..."

    cat > infrastructure/terraform/tenants/${tenant_name}.tfvars <<EOF
# Tenant configuration for ${display_name}
# Generated on $(date)

tenants = {
  "${tenant_name}" = {
    # Basic Information
    display_name = "${display_name}"
    subdomain    = "${tenant_name}"
    tier         = "${tier}"

    # Infrastructure Configuration (based on tier: ${tier})
$(case $tier in
    enterprise)
        cat <<ENTERPRISE
    rds_instance_class      = "db.r6g.xlarge"
    rds_allocated_storage   = 100
    rds_max_storage        = 1000
    rds_backup_retention   = 30
    rds_multi_az          = true

    redis_node_type       = "cache.r7g.large"
    redis_num_cache_nodes = 2

    django_desired_count  = 3
    django_cpu           = 1024
    django_memory        = 2048

    celery_desired_count = 2
    celery_cpu          = 512
    celery_memory       = 1024

    enable_autoscaling     = true
    min_capacity          = 2
    max_capacity          = 10
    target_cpu_utilization = 70
ENTERPRISE
        ;;
    standard)
        cat <<STANDARD
    rds_instance_class      = "db.t4g.medium"
    rds_allocated_storage   = 20
    rds_max_storage        = 100
    rds_backup_retention   = 7
    rds_multi_az          = false

    redis_node_type       = "cache.t4g.small"
    redis_num_cache_nodes = 1

    django_desired_count  = 2
    django_cpu           = 512
    django_memory        = 1024

    celery_desired_count = 1
    celery_cpu          = 256
    celery_memory       = 512

    enable_autoscaling     = true
    min_capacity          = 1
    max_capacity          = 5
    target_cpu_utilization = 75
STANDARD
        ;;
    trial)
        cat <<TRIAL
    use_shared_rds = true
    use_shared_redis = true

    django_desired_count  = 1
    django_cpu           = 256
    django_memory        = 512

    celery_desired_count = 1
    celery_cpu          = 256
    celery_memory       = 512

    enable_autoscaling = false
TRIAL
        ;;
esac)

    # Storage Configuration
    s3_versioning        = true
    s3_lifecycle_rules   = $([ "$tier" = "enterprise" ] && echo "true" || echo "false")
    efs_throughput_mode  = "$([ "$tier" = "enterprise" ] && echo "provisioned" || echo "bursting")"
    $([ "$tier" = "enterprise" ] && echo "efs_throughput_mibps = 100")

    # HIPAA Compliance
    hipaa_compliant      = true
    enable_audit_logging = true
    enable_flow_logs     = $([ "$tier" != "trial" ] && echo "true" || echo "false")
    data_retention_days  = 2555  # 7 years for HIPAA

    # Contact Information
    technical_contact = "${contact_email}"
    billing_contact   = "${contact_email}"

    # Cost allocation tags
    cost_center = "${tenant_name}"
    department  = "healthcare"
  }
}
EOF

    print_message "$GREEN" "Configuration file created: infrastructure/terraform/tenants/${tenant_name}.tfvars"
}

# Function to provision infrastructure
provision_infrastructure() {
    local tenant_name=$1

    print_message "$YELLOW" "Provisioning AWS infrastructure for tenant: $tenant_name..."

    cd infrastructure/terraform

    # Initialize Terraform
    terraform init

    # Plan with the tenant configuration
    terraform plan \
        -var-file="tenants/${tenant_name}.tfvars" \
        -target="module.tenant[\"$tenant_name\"]" \
        -out="${tenant_name}.tfplan"

    # Ask for confirmation
    print_message "$YELLOW" "Review the plan above. Do you want to proceed with provisioning? (yes/no)"
    read -r confirmation

    if [ "$confirmation" != "yes" ]; then
        print_message "$RED" "Provisioning cancelled"
        exit 1
    fi

    # Apply the configuration
    terraform apply "${tenant_name}.tfplan"

    cd ../..

    print_message "$GREEN" "Infrastructure provisioned successfully"
}

# Function to create tenant in database
create_tenant_database_record() {
    local tenant_name=$1
    local display_name=$2
    local subdomain=$3

    print_message "$YELLOW" "Creating tenant record in database..."

    # Create Python script to add tenant
    cat > /tmp/create_tenant.py <<EOF
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from mate.tenants.models import Tenant

tenant = Tenant.objects.create(
    name="${display_name}",
    slug="${tenant_name}",
    subdomain="${subdomain}",
    deployment_status="provisioning",
    is_active=False,
    aws_region=os.environ.get('AWS_REGION', 'us-east-1'),
    plan="${tier}",
    hipaa_compliant=True,
)

print(f"Tenant created with ID: {tenant.id}")
EOF

    # Run the script
    python /tmp/create_tenant.py

    # Clean up
    rm /tmp/create_tenant.py

    print_message "$GREEN" "Tenant record created"
}

# Function to configure Cognito for SSO
configure_cognito_sso() {
    local tenant_name=$1
    local identity_provider_type=$2

    if [ "$identity_provider_type" = "none" ]; then
        print_message "$YELLOW" "Skipping SSO configuration (using Cognito native auth)"
        return
    fi

    print_message "$YELLOW" "Configuring Cognito SSO for tenant: $tenant_name..."

    # Get Cognito User Pool ID from Terraform output
    local user_pool_id=$(cd infrastructure/terraform && terraform output -raw cognito_user_pool_id)

    if [ "$identity_provider_type" = "saml" ]; then
        print_message "$BLUE" "Please provide the following SAML configuration:"
        echo "1. SAML Metadata URL or XML file path:"
        read -r saml_metadata

        # Create SAML provider in Cognito
        aws cognito-idp create-identity-provider \
            --user-pool-id "$user_pool_id" \
            --provider-name "${tenant_name}_saml" \
            --provider-type SAML \
            --provider-details "MetadataURL=${saml_metadata}" \
            --attribute-mapping email=email,name=name
    fi

    print_message "$GREEN" "SSO configuration completed"
}

# Function to run initial migrations
run_initial_setup() {
    local tenant_name=$1

    print_message "$YELLOW" "Running initial setup for tenant: $tenant_name..."

    # Run database migrations
    ./scripts/deploy.sh migrate $tenant_name

    # Create superuser
    print_message "$YELLOW" "Creating superuser account..."
    aws ecs run-task \
        --cluster mate-production \
        --task-definition mate-${tenant_name}-production-django \
        --launch-type FARGATE \
        --overrides '{
            "containerOverrides": [{
                "name": "django",
                "command": ["python", "manage.py", "createsuperuser", "--noinput", "--email", "admin@'${tenant_name}'.com"]
            }]
        }'

    print_message "$GREEN" "Initial setup completed"
}

# Main provisioning flow
main() {
    print_message "$GREEN" "=========================================="
    print_message "$GREEN" "MATE Tenant Provisioning Script"
    print_message "$GREEN" "=========================================="

    # Collect tenant information
    print_message "$BLUE" "Please provide the following information:"

    echo -n "Tenant name (lowercase, hyphens allowed): "
    read -r tenant_name

    echo -n "Display name: "
    read -r display_name

    echo -n "Tier (trial/standard/enterprise): "
    read -r tier

    echo -n "Contact email: "
    read -r contact_email

    echo -n "Configure SSO? (none/saml/oidc): "
    read -r sso_type

    # Validate inputs
    if [[ ! "$tenant_name" =~ ^[a-z0-9-]+$ ]]; then
        print_message "$RED" "Invalid tenant name. Use only lowercase letters, numbers, and hyphens."
        exit 1
    fi

    if [[ ! "$tier" =~ ^(trial|standard|enterprise)$ ]]; then
        print_message "$RED" "Invalid tier. Must be: trial, standard, or enterprise"
        exit 1
    fi

    # Summary
    print_message "$YELLOW" "=========================================="
    print_message "$YELLOW" "Provisioning Summary:"
    print_message "$YELLOW" "Tenant Name: $tenant_name"
    print_message "$YELLOW" "Display Name: $display_name"
    print_message "$YELLOW" "Tier: $tier"
    print_message "$YELLOW" "Contact: $contact_email"
    print_message "$YELLOW" "SSO: $sso_type"
    print_message "$YELLOW" "=========================================="

    echo -n "Proceed with provisioning? (yes/no): "
    read -r confirmation

    if [ "$confirmation" != "yes" ]; then
        print_message "$RED" "Provisioning cancelled"
        exit 1
    fi

    # Execute provisioning steps
    create_tenant_config "$tenant_name" "$display_name" "$tier" "$contact_email"
    provision_infrastructure "$tenant_name"
    create_tenant_database_record "$tenant_name" "$display_name" "$tenant_name"
    configure_cognito_sso "$tenant_name" "$sso_type"
    run_initial_setup "$tenant_name"

    # Final summary
    print_message "$GREEN" "=========================================="
    print_message "$GREEN" "Tenant Provisioning Complete!"
    print_message "$GREEN" "=========================================="
    print_message "$GREEN" "Tenant: $display_name"
    print_message "$GREEN" "URL: https://${tenant_name}.mate.consensusai.com"
    print_message "$GREEN" "Status: Active"
    print_message "$GREEN" ""
    print_message "$YELLOW" "Next steps:"
    print_message "$YELLOW" "1. Share the URL with the tenant administrator"
    print_message "$YELLOW" "2. Configure any additional SSO settings if needed"
    print_message "$YELLOW" "3. Monitor the deployment in AWS Console"
}

# Run main function
main
