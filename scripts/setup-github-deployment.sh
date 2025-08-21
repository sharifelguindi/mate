#!/bin/bash
set -e

# Setup script for GitHub Actions deployment
# This script configures AWS resources and GitHub secrets for CI/CD

echo "🚀 MATE GitHub Actions Deployment Setup"
echo "======================================="

# Check prerequisites
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI is required but not installed. Aborting." >&2; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "❌ GitHub CLI is required but not installed. Aborting." >&2; exit 1; }

# Configuration
read -p "Enter your AWS Account ID: " AWS_ACCOUNT_ID
read -p "Enter your GitHub repository (owner/repo): " GITHUB_REPO
read -p "Enter environment (dev/staging/production): " ENVIRONMENT

echo ""
echo "📋 Configuration Summary:"
echo "  AWS Account: $AWS_ACCOUNT_ID"
echo "  Repository: $GITHUB_REPO"
echo "  Environment: $ENVIRONMENT"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Setup cancelled"
    exit 1
fi

# Create IAM user for GitHub Actions
echo ""
echo "1️⃣ Creating IAM user for GitHub Actions..."
aws iam create-user --user-name github-actions-$ENVIRONMENT 2>/dev/null || echo "User already exists"

# Create and attach policy
echo "2️⃣ Creating IAM policy..."
cat > /tmp/github-actions-policy.json <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecs:UpdateService",
                "ecs:DescribeServices",
                "ecs:DescribeTaskDefinition",
                "ecs:RegisterTaskDefinition",
                "ecs:RunTask",
                "ecs:DescribeTasks",
                "ecs:ListTasks",
                "ecs:StopTask"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": [
                "arn:aws:iam::${AWS_ACCOUNT_ID}:role/mate-*-ecs-task-execution",
                "arn:aws:iam::${AWS_ACCOUNT_ID}:role/mate-*-ecs-task"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData",
                "cloudwatch:GetMetricStatistics",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "elasticloadbalancing:DescribeTargetGroups",
                "elasticloadbalancing:DescribeTargetHealth"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "rds:DescribeDBInstances",
                "rds:CreateDBSnapshot"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:*:${AWS_ACCOUNT_ID}:secret:mate-*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem"
            ],
            "Resource": "arn:aws:dynamodb:*:${AWS_ACCOUNT_ID}:table/mate-deployments"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups"
            ],
            "Resource": "*"
        }
    ]
}
EOF

POLICY_ARN=$(aws iam create-policy \
    --policy-name github-actions-$ENVIRONMENT \
    --policy-document file:///tmp/github-actions-policy.json \
    --query 'Policy.Arn' \
    --output text 2>/dev/null || \
    aws iam list-policies --query "Policies[?PolicyName=='github-actions-$ENVIRONMENT'].Arn" --output text)

echo "   Policy ARN: $POLICY_ARN"

aws iam attach-user-policy \
    --user-name github-actions-$ENVIRONMENT \
    --policy-arn $POLICY_ARN

# Create access key
echo "3️⃣ Creating access key..."
ACCESS_KEY_JSON=$(aws iam create-access-key --user-name github-actions-$ENVIRONMENT)
ACCESS_KEY_ID=$(echo $ACCESS_KEY_JSON | jq -r '.AccessKey.AccessKeyId')
SECRET_ACCESS_KEY=$(echo $ACCESS_KEY_JSON | jq -r '.AccessKey.SecretAccessKey')

# Create DynamoDB table for deployment tracking
echo "4️⃣ Creating DynamoDB table for deployment tracking..."
aws dynamodb create-table \
    --table-name mate-deployments \
    --attribute-definitions \
        AttributeName=deployment_id,AttributeType=S \
    --key-schema \
        AttributeName=deployment_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --tags Key=Environment,Value=$ENVIRONMENT Key=ManagedBy,Value=Terraform 2>/dev/null || echo "Table already exists"

# Set GitHub secrets
echo "5️⃣ Setting GitHub secrets..."
gh secret set AWS_ACCOUNT_ID --body "$AWS_ACCOUNT_ID" --repo $GITHUB_REPO
gh secret set AWS_ACCESS_KEY_ID --body "$ACCESS_KEY_ID" --repo $GITHUB_REPO
gh secret set AWS_SECRET_ACCESS_KEY --body "$SECRET_ACCESS_KEY" --repo $GITHUB_REPO

# Create GitHub environments
echo "6️⃣ Creating GitHub environments..."
for env in development staging production; do
    gh api -X PUT /repos/$GITHUB_REPO/environments/$env \
        --field wait_timer=0 \
        --field deployment_branch_policy='{"protected_branches":false,"custom_branch_policies":true}'
done

# Add protection rules for production
echo "7️⃣ Adding protection rules for production..."
gh api -X PUT /repos/$GITHUB_REPO/environments/production \
    --field wait_timer=10 \
    --field reviewers='[]' \
    --field deployment_branch_policy='{"protected_branches":true,"custom_branch_policies":false}'

# Initial ECR repository push
echo "8️⃣ Building and pushing initial Docker images..."
AWS_REGION=us-east-1
ECR_REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push images
for SERVICE in web celery beat; do
    echo "   Building $SERVICE..."
    docker build -f compose/production/django/Dockerfile \
        --target ${SERVICE} \
        -t $ECR_REGISTRY/mate-${SERVICE}-${ENVIRONMENT}:latest \
        -t $ECR_REGISTRY/mate-${SERVICE}-${ENVIRONMENT}:initial \
        .

    echo "   Pushing $SERVICE..."
    docker push $ECR_REGISTRY/mate-${SERVICE}-${ENVIRONMENT}:latest
    docker push $ECR_REGISTRY/mate-${SERVICE}-${ENVIRONMENT}:initial
done

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📝 Next Steps:"
echo "1. Review and customize the GitHub Actions workflows in .github/workflows/"
echo "2. Add a Slack webhook URL as a GitHub secret (optional):"
echo "   gh secret set SLACK_WEBHOOK --body 'YOUR_WEBHOOK_URL' --repo $GITHUB_REPO"
echo "3. Add required reviewers for production environment:"
echo "   gh api -X PUT /repos/$GITHUB_REPO/environments/production --field reviewers='[\"username\"]'"
echo "4. Commit and push the changes to trigger the CI/CD pipeline:"
echo "   git add ."
echo "   git commit -m 'Add GitHub Actions CI/CD pipeline'"
echo "   git push origin main"
echo ""
echo "🔗 Useful Links:"
echo "  GitHub Actions: https://github.com/$GITHUB_REPO/actions"
echo "  AWS ECS Console: https://console.aws.amazon.com/ecs"
echo "  CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#logsV2:log-groups"
