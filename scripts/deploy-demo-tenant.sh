#!/bin/bash
set -e

echo "==========================================="
echo "MATE Demo Tenant Infrastructure Deployment"
echo "==========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to tenant terraform directory
cd infrastructure/terraform/tenants/demo

echo -e "${YELLOW}Step 1: Initializing Terraform...${NC}"
terraform init

echo -e "${YELLOW}Step 2: Planning infrastructure changes...${NC}"
terraform plan -out=tfplan

echo -e "${YELLOW}Step 3: Review the plan above. Deploy? (yes/no)${NC}"
read -r response
if [[ "$response" != "yes" ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 4: Applying infrastructure...${NC}"
terraform apply tfplan

echo -e "${GREEN}Step 5: Verifying deployment...${NC}"

# Get outputs
ALB_DNS=$(terraform output -raw alb_dns_name 2>/dev/null || echo "Not available")
RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null || echo "Not available")
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint 2>/dev/null || echo "Not available")

echo "==========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "==========================================="
echo "Infrastructure Outputs:"
echo "  ALB DNS: $ALB_DNS"
echo "  RDS Endpoint: $RDS_ENDPOINT"
echo "  Redis Endpoint: $REDIS_ENDPOINT"
echo ""
echo "Next Steps:"
echo "1. Wait 2-3 minutes for services to stabilize"
echo "2. Check ECS services: aws ecs list-services --cluster mate-dev"
echo "3. Re-enable CI/CD pipeline steps in .github/workflows/ci-cd.yml"
echo "4. Push code to trigger deployment"
