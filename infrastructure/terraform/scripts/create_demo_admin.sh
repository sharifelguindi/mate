#!/bin/bash
# Script to create admin user for demo tenant on AWS

set -e

CLUSTER="mate-production"
TASK_DEFINITION="mate-demo-production-django"
REGION="us-east-1"

echo "Creating admin user for demo tenant..."

# Get network configuration from existing service
SERVICE_NAME="mate-demo-production-django"
NETWORK_CONFIG=$(aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE_NAME \
  --region $REGION \
  --query "services[0].networkConfiguration.awsvpcConfiguration" \
  --output json)

# Run the management command
TASK_ARN=$(aws ecs run-task \
  --cluster $CLUSTER \
  --task-definition $TASK_DEFINITION \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration=$NETWORK_CONFIG" \
  --overrides '{
    "containerOverrides": [{
      "name": "django",
      "command": [
        "python", "manage.py", "create_tenant_admin",
        "--username", "admin",
        "--email", "admin@demo.mate.sociant.ai",
        "--force-password-change",
        "--output-password"
      ],
      "environment": [
        {"name": "DJANGO_SETTINGS_MODULE", "value": "config.settings.production"}
      ]
    }]
  }' \
  --region $REGION \
  --query "tasks[0].taskArn" \
  --output text)

echo "Task started: $TASK_ARN"
echo "Waiting for task to complete..."

# Wait for task to complete
aws ecs wait tasks-stopped \
  --cluster $CLUSTER \
  --tasks $TASK_ARN \
  --region $REGION

# Get the logs
LOG_GROUP="/ecs/mate-demo-production"
LOG_STREAM=$(aws logs describe-log-streams \
  --log-group-name $LOG_GROUP \
  --order-by LastEventTime \
  --descending \
  --limit 1 \
  --query "logStreams[0].logStreamName" \
  --output text)

echo ""
echo "Task output:"
aws logs get-log-events \
  --log-group-name $LOG_GROUP \
  --log-stream-name $LOG_STREAM \
  --start-from-head \
  --query "events[*].message" \
  --output text

echo ""
echo "Admin user creation complete!"
echo "The password was displayed above (look for PASSWORD=...)"
echo "User must change password on first login."
