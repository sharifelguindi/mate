#!/bin/bash
# Deployment script for MATE multi-tenant ECS infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REGISTRY=${ECR_REGISTRY:-}
ENVIRONMENT=${ENVIRONMENT:-production}
TENANT_NAME=${TENANT_NAME:-}

# Function to print colored messages
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_message "$YELLOW" "Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_message "$RED" "AWS CLI is not installed"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_message "$RED" "Docker is not installed"
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        print_message "$RED" "Terraform is not installed"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_message "$RED" "AWS credentials not configured"
        exit 1
    fi
    
    print_message "$GREEN" "All prerequisites met"
}

# Function to build and push Docker images
build_and_push_images() {
    print_message "$YELLOW" "Building and pushing Docker images..."
    
    # Get ECR login token
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    
    # Build Django image
    print_message "$YELLOW" "Building Django image..."
    docker build -f compose/production/django/Dockerfile \
        --build-arg BUILD_ENVIRONMENT=production \
        -t $ECR_REGISTRY/mate-web:latest \
        -t $ECR_REGISTRY/mate-web:$(git rev-parse --short HEAD) .
    
    # Push Django image
    print_message "$YELLOW" "Pushing Django image..."
    docker push $ECR_REGISTRY/mate-web:latest
    docker push $ECR_REGISTRY/mate-web:$(git rev-parse --short HEAD)
    
    # Tag for Celery (same image, different entrypoint)
    docker tag $ECR_REGISTRY/mate-web:latest $ECR_REGISTRY/mate-celery:latest
    docker tag $ECR_REGISTRY/mate-web:latest $ECR_REGISTRY/mate-beat:latest
    
    # Push Celery and Beat images
    docker push $ECR_REGISTRY/mate-celery:latest
    docker push $ECR_REGISTRY/mate-beat:latest
    
    print_message "$GREEN" "Images built and pushed successfully"
}

# Function to run database migrations
run_migrations() {
    local tenant=$1
    print_message "$YELLOW" "Running database migrations for tenant: $tenant..."
    
    # Run migrations using ECS task
    aws ecs run-task \
        --cluster mate-$ENVIRONMENT \
        --task-definition mate-$tenant-$ENVIRONMENT-django \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$(terraform output -raw private_subnet_ids)],securityGroups=[$(terraform output -raw django_security_group_id)]}" \
        --overrides '{
            "containerOverrides": [{
                "name": "django",
                "command": ["python", "manage.py", "migrate", "--noinput"]
            }]
        }' \
        --region $AWS_REGION
    
    print_message "$GREEN" "Migrations completed"
}

# Function to deploy infrastructure for a tenant
deploy_tenant_infrastructure() {
    local tenant=$1
    print_message "$YELLOW" "Deploying infrastructure for tenant: $tenant..."
    
    cd infrastructure/terraform
    
    # Initialize Terraform if needed
    terraform init
    
    # Plan deployment
    terraform plan -var="environment=$ENVIRONMENT" -target="module.tenant[\"$tenant\"]" -out=tfplan
    
    # Apply deployment
    terraform apply tfplan
    
    # Get outputs
    local alb_dns=$(terraform output -json tenant_endpoints | jq -r ".$tenant.alb_dns")
    local web_url=$(terraform output -json tenant_endpoints | jq -r ".$tenant.web_url")
    
    print_message "$GREEN" "Infrastructure deployed for $tenant"
    print_message "$GREEN" "ALB DNS: $alb_dns"
    print_message "$GREEN" "Web URL: $web_url"
    
    cd ../..
}

# Function to update ECS service
update_ecs_service() {
    local tenant=$1
    local service=$2
    
    print_message "$YELLOW" "Updating ECS service: $service for tenant: $tenant..."
    
    aws ecs update-service \
        --cluster mate-$ENVIRONMENT \
        --service mate-$tenant-$ENVIRONMENT-$service \
        --force-new-deployment \
        --region $AWS_REGION
    
    # Wait for service to stabilize
    aws ecs wait services-stable \
        --cluster mate-$ENVIRONMENT \
        --services mate-$tenant-$ENVIRONMENT-$service \
        --region $AWS_REGION
    
    print_message "$GREEN" "Service $service updated successfully"
}

# Function to deploy a tenant
deploy_tenant() {
    local tenant=$1
    
    print_message "$YELLOW" "=========================================="
    print_message "$YELLOW" "Deploying tenant: $tenant"
    print_message "$YELLOW" "=========================================="
    
    # Deploy infrastructure
    deploy_tenant_infrastructure $tenant
    
    # Run migrations
    run_migrations $tenant
    
    # Update services
    update_ecs_service $tenant django
    update_ecs_service $tenant celery
    update_ecs_service $tenant beat
    
    print_message "$GREEN" "Tenant $tenant deployed successfully!"
}

# Function to deploy all tenants
deploy_all_tenants() {
    print_message "$YELLOW" "Deploying all tenants..."
    
    # Get list of tenants from Terraform
    cd infrastructure/terraform
    local tenants=$(terraform output -json tenant_endpoints | jq -r 'keys[]')
    cd ../..
    
    for tenant in $tenants; do
        deploy_tenant $tenant
    done
}

# Main deployment flow
main() {
    print_message "$GREEN" "=========================================="
    print_message "$GREEN" "MATE Multi-Tenant Deployment Script"
    print_message "$GREEN" "=========================================="
    
    # Check prerequisites
    check_prerequisites
    
    # Parse command line arguments
    case "$1" in
        build)
            build_and_push_images
            ;;
        tenant)
            if [ -z "$2" ]; then
                print_message "$RED" "Please specify tenant name"
                exit 1
            fi
            build_and_push_images
            deploy_tenant $2
            ;;
        all)
            build_and_push_images
            deploy_all_tenants
            ;;
        migrate)
            if [ -z "$2" ]; then
                print_message "$RED" "Please specify tenant name"
                exit 1
            fi
            run_migrations $2
            ;;
        update-service)
            if [ -z "$2" ] || [ -z "$3" ]; then
                print_message "$RED" "Usage: $0 update-service <tenant> <service>"
                exit 1
            fi
            update_ecs_service $2 $3
            ;;
        *)
            print_message "$YELLOW" "Usage: $0 {build|tenant <name>|all|migrate <tenant>|update-service <tenant> <service>}"
            echo ""
            echo "Commands:"
            echo "  build              - Build and push Docker images"
            echo "  tenant <name>      - Deploy a specific tenant"
            echo "  all                - Deploy all tenants"
            echo "  migrate <tenant>   - Run database migrations for a tenant"
            echo "  update-service     - Update a specific ECS service"
            exit 1
            ;;
    esac
    
    print_message "$GREEN" "Deployment completed successfully!"
}

# Run main function
main "$@"