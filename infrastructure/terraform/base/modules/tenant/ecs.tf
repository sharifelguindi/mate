# ECS Task Definitions and Services for tenant

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "django" {
  name              = "/ecs/${local.tenant_prefix}/django"
  retention_in_days = local.config.hipaa_compliant ? local.config.data_retention_days : 30
  kms_key_id       = var.kms_key_id

  tags = {
    Name   = "${local.tenant_prefix}-django-logs"
    Tenant = var.tenant_name
  }
}

resource "aws_cloudwatch_log_group" "celery" {
  name              = "/ecs/${local.tenant_prefix}/celery"
  retention_in_days = local.config.hipaa_compliant ? local.config.data_retention_days : 30
  kms_key_id       = var.kms_key_id

  tags = {
    Name   = "${local.tenant_prefix}-celery-logs"
    Tenant = var.tenant_name
  }
}

resource "aws_cloudwatch_log_group" "beat" {
  name              = "/ecs/${local.tenant_prefix}/beat"
  retention_in_days = local.config.hipaa_compliant ? local.config.data_retention_days : 30
  kms_key_id       = var.kms_key_id

  tags = {
    Name   = "${local.tenant_prefix}-beat-logs"
    Tenant = var.tenant_name
  }
}

# IAM Role for ECS Tasks
resource "aws_iam_role" "ecs_task_execution" {
  name = "${local.tenant_prefix}-ecs-task-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name   = "${local.tenant_prefix}-ecs-task-execution"
    Tenant = var.tenant_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for Secrets Manager and KMS
resource "aws_iam_role_policy" "ecs_task_execution_secrets" {
  name = "${local.tenant_prefix}-ecs-secrets"
  role = aws_iam_role.ecs_task_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ]
        Resource = [
          aws_secretsmanager_secret.django.arn,
          aws_secretsmanager_secret.db.arn,
          aws_secretsmanager_secret.redis.arn,
          var.kms_key_id
        ]
      }
    ]
  })
}

# IAM Role for ECS Tasks (application permissions)
resource "aws_iam_role" "ecs_task" {
  name = "${local.tenant_prefix}-ecs-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name   = "${local.tenant_prefix}-ecs-task"
    Tenant = var.tenant_name
  }
}

# S3 permissions for the application
resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "${local.tenant_prefix}-ecs-s3"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.tenant_data.arn,
          "${aws_s3_bucket.tenant_data.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [var.kms_key_id]
      }
    ]
  })
}

# EFS permissions for mounted volumes
resource "aws_iam_role_policy" "ecs_task_efs" {
  name = "${local.tenant_prefix}-ecs-efs"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite",
          "elasticfilesystem:DescribeMountTargets"
        ]
        Resource = [
          aws_efs_file_system.models.arn,
          aws_efs_file_system.tenant_data.arn
        ]
      }
    ]
  })
}

# SES permissions for email
resource "aws_iam_role_policy" "ecs_task_ses" {
  name = "${local.tenant_prefix}-ecs-ses"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ses:FromAddress" = "noreply@${var.domain_name}"
          }
        }
      }
    ]
  })
}

# CloudWatch logs permissions for watchtower
resource "aws_iam_role_policy" "ecs_task_cloudwatch" {
  name = "${local.tenant_prefix}-ecs-cloudwatch"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${local.tenant_prefix}/*",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${local.tenant_prefix}/*:*"
        ]
      }
    ]
  })
}

# Django Secrets
resource "aws_secretsmanager_secret" "django" {
  name                    = "${local.tenant_prefix}-django-secrets"
  recovery_window_in_days = 7
  kms_key_id             = var.kms_key_id

  tags = {
    Name   = "${local.tenant_prefix}-django-secrets"
    Tenant = var.tenant_name
  }
}

resource "random_password" "django_secret_key" {
  length  = 50
  special = true
}

resource "aws_secretsmanager_secret_version" "django" {
  secret_id = aws_secretsmanager_secret.django.id
  secret_string = jsonencode({
    DJANGO_SECRET_KEY = random_password.django_secret_key.result
    COGNITO_APP_CLIENT_SECRET = var.cognito_app_client_secret
  })
}

# ECS Task Definition - Django
resource "aws_ecs_task_definition" "django" {
  family                   = "${local.tenant_prefix}-django"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = local.config.django_cpu
  memory                  = local.config.django_memory
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  task_role_arn          = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "django"
      image = "${var.ecr_repositories["mate-django"]}:latest"

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "config.settings.production"
        },
        {
          name  = "TENANT_SUBDOMAIN"
          value = var.tenant_config.subdomain
        },
        {
          name  = "TENANT_NAME"
          value = var.tenant_name
        },
        {
          name  = "AWS_STORAGE_BUCKET_NAME"
          value = aws_s3_bucket.tenant_data.bucket
        },
        {
          name  = "AWS_S3_REGION_NAME"
          value = var.aws_region
        },
        {
          name  = "DJANGO_ALLOWED_HOSTS"
          value = "${var.tenant_config.subdomain}.${var.domain_name},${aws_lb.tenant.dns_name},localhost,127.0.0.1,10.0.10.100,10.0.20.100"
        },
        {
          name  = "COGNITO_DOMAIN"
          value = var.cognito_user_pool_domain
        },
        {
          name  = "COGNITO_USER_POOL_ID"
          value = var.cognito_user_pool_id
        },
        {
          name  = "COGNITO_APP_CLIENT_ID"
          value = var.cognito_app_client_id
        },
        {
          name  = "CLOUDWATCH_LOG_GROUP"
          value = aws_cloudwatch_log_group.django.name
        },
        {
          name  = "CLOUDWATCH_LOG_STREAM"
          value = var.tenant_name
        },
        {
          name  = "DJANGO_AWS_ACCESS_KEY_ID"
          value = ""
        },
        {
          name  = "DJANGO_AWS_SECRET_ACCESS_KEY"
          value = ""
        }
      ]

      secrets = [
        {
          name      = "DJANGO_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.django.arn}:DJANGO_SECRET_KEY::"
        },
        {
          name      = "COGNITO_APP_CLIENT_SECRET"
          valueFrom = "${aws_secretsmanager_secret.django.arn}:COGNITO_APP_CLIENT_SECRET::"
        },
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:connection_string::"
        },
        {
          name      = "POSTGRES_USER"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:username::"
        },
        {
          name      = "POSTGRES_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:password::"
        },
        {
          name      = "POSTGRES_HOST"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:host::"
        },
        {
          name      = "POSTGRES_PORT"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:port::"
        },
        {
          name      = "POSTGRES_DB"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:database::"
        },
        {
          name      = "REDIS_URL"
          valueFrom = "${aws_secretsmanager_secret.redis.arn}:connection_string::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.django.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "django"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health/ || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }

      mountPoints = [
        {
          sourceVolume  = "efs-models"
          containerPath = "/mnt/efs/models"
          readOnly      = true
        },
        {
          sourceVolume  = "efs-tenant-data"
          containerPath = "/mnt/efs/tenant-data"
          readOnly      = false
        }
      ]
    }
  ])

  volume {
    name = "efs-models"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.models.id
      transit_encryption = "ENABLED"
      authorization_config {
        iam = "ENABLED"
      }
    }
  }

  volume {
    name = "efs-tenant-data"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.tenant_data.id
      transit_encryption = "ENABLED"
      authorization_config {
        iam = "ENABLED"
      }
    }
  }

  tags = {
    Name   = "${local.tenant_prefix}-django"
    Tenant = var.tenant_name
  }
}

# ECS Service - Django
resource "aws_ecs_service" "django" {
  name            = "${local.tenant_prefix}-django"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.django.arn
  desired_count   = local.config.django_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tenant.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.django.arn
    container_name   = "django"
    container_port   = 8000
  }

  health_check_grace_period_seconds = 60

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"

  tags = {
    Name   = "${local.tenant_prefix}-django"
    Tenant = var.tenant_name
  }

  depends_on = [
    aws_lb_listener.https,
    aws_iam_role_policy.ecs_task_s3,
    aws_iam_role_policy.ecs_task_ses
  ]
}

# ECS Task Definition - Celery Worker
resource "aws_ecs_task_definition" "celery" {
  family                   = "${local.tenant_prefix}-celery"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = tostring(coalesce(local.config.celery_cpu, 256))
  memory                  = tostring(coalesce(local.config.celery_memory, 512))
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  task_role_arn          = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "celery"
      image = "${var.ecr_repositories["mate-celery"]}:latest"
      command = ["/start-celeryworker"]

      environment = [
        {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "config.settings.production"
        },
        {
          name  = "TENANT_SUBDOMAIN"
          value = var.tenant_config.subdomain
        },
        {
          name  = "TENANT_NAME"
          value = var.tenant_name
        },
        {
          name  = "AWS_STORAGE_BUCKET_NAME"
          value = aws_s3_bucket.tenant_data.bucket
        },
        {
          name  = "AWS_S3_REGION_NAME"
          value = var.aws_region
        },
        {
          name  = "DJANGO_ALLOWED_HOSTS"
          value = "${var.tenant_config.subdomain}.${var.domain_name},${aws_lb.tenant.dns_name},localhost,127.0.0.1,10.0.10.100,10.0.20.100"
        },
        {
          name  = "COGNITO_DOMAIN"
          value = var.cognito_user_pool_domain
        },
        {
          name  = "COGNITO_USER_POOL_ID"
          value = var.cognito_user_pool_id
        },
        {
          name  = "COGNITO_APP_CLIENT_ID"
          value = var.cognito_app_client_id
        },
        {
          name  = "CLOUDWATCH_LOG_GROUP"
          value = aws_cloudwatch_log_group.celery.name
        },
        {
          name  = "CLOUDWATCH_LOG_STREAM"
          value = var.tenant_name
        },
        {
          name  = "DJANGO_AWS_ACCESS_KEY_ID"
          value = ""
        },
        {
          name  = "DJANGO_AWS_SECRET_ACCESS_KEY"
          value = ""
        }
      ]

      secrets = [
        {
          name      = "DJANGO_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.django.arn}:DJANGO_SECRET_KEY::"
        },
        {
          name      = "COGNITO_APP_CLIENT_SECRET"
          valueFrom = "${aws_secretsmanager_secret.django.arn}:COGNITO_APP_CLIENT_SECRET::"
        },
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:connection_string::"
        },
        {
          name      = "POSTGRES_USER"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:username::"
        },
        {
          name      = "POSTGRES_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:password::"
        },
        {
          name      = "POSTGRES_HOST"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:host::"
        },
        {
          name      = "POSTGRES_PORT"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:port::"
        },
        {
          name      = "POSTGRES_DB"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:database::"
        },
        {
          name      = "REDIS_URL"
          valueFrom = "${aws_secretsmanager_secret.redis.arn}:connection_string::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.celery.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "celery"
        }
      }

      mountPoints = [
        {
          sourceVolume  = "efs-models"
          containerPath = "/mnt/efs/models"
          readOnly      = true
        },
        {
          sourceVolume  = "efs-tenant-data"
          containerPath = "/mnt/efs/tenant-data"
          readOnly      = false
        }
      ]
    }
  ])

  volume {
    name = "efs-models"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.models.id
      transit_encryption = "ENABLED"
      authorization_config {
        iam = "ENABLED"
      }
    }
  }

  volume {
    name = "efs-tenant-data"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.tenant_data.id
      transit_encryption = "ENABLED"
      authorization_config {
        iam = "ENABLED"
      }
    }
  }

  tags = {
    Name   = "${local.tenant_prefix}-celery"
    Tenant = var.tenant_name
  }
}

# ECS Service - Celery Worker
resource "aws_ecs_service" "celery" {
  name            = "${local.tenant_prefix}-celery"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.celery.arn
  desired_count   = local.config.celery_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tenant.id]
    assign_public_ip = false
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"

  tags = {
    Name   = "${local.tenant_prefix}-celery"
    Tenant = var.tenant_name
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_task_execution,
    aws_iam_role_policy.ecs_task_s3,
    aws_iam_role_policy.ecs_task_cloudwatch
  ]
}

# ECS Task Definition - Celery Beat
resource "aws_ecs_task_definition" "beat" {
  family                   = "${local.tenant_prefix}-beat"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = tostring(coalesce(local.config.beat_cpu, 256))
  memory                  = tostring(coalesce(local.config.beat_memory, 512))
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  task_role_arn          = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "beat"
      image = "${var.ecr_repositories["mate-beat"]}:latest"
      command = ["/start-celerybeat"]

      environment = [
        {
          name  = "DJANGO_SETTINGS_MODULE"
          value = "config.settings.production"
        },
        {
          name  = "TENANT_SUBDOMAIN"
          value = var.tenant_config.subdomain
        },
        {
          name  = "TENANT_NAME"
          value = var.tenant_name
        },
        {
          name  = "AWS_STORAGE_BUCKET_NAME"
          value = aws_s3_bucket.tenant_data.bucket
        },
        {
          name  = "AWS_S3_REGION_NAME"
          value = var.aws_region
        },
        {
          name  = "DJANGO_ALLOWED_HOSTS"
          value = "${var.tenant_config.subdomain}.${var.domain_name},${aws_lb.tenant.dns_name},localhost,127.0.0.1,10.0.10.100,10.0.20.100"
        },
        {
          name  = "COGNITO_DOMAIN"
          value = var.cognito_user_pool_domain
        },
        {
          name  = "COGNITO_USER_POOL_ID"
          value = var.cognito_user_pool_id
        },
        {
          name  = "COGNITO_APP_CLIENT_ID"
          value = var.cognito_app_client_id
        },
        {
          name  = "CLOUDWATCH_LOG_GROUP"
          value = aws_cloudwatch_log_group.beat.name
        },
        {
          name  = "CLOUDWATCH_LOG_STREAM"
          value = var.tenant_name
        },
        {
          name  = "DJANGO_AWS_ACCESS_KEY_ID"
          value = ""
        },
        {
          name  = "DJANGO_AWS_SECRET_ACCESS_KEY"
          value = ""
        }
      ]

      secrets = [
        {
          name      = "DJANGO_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.django.arn}:DJANGO_SECRET_KEY::"
        },
        {
          name      = "COGNITO_APP_CLIENT_SECRET"
          valueFrom = "${aws_secretsmanager_secret.django.arn}:COGNITO_APP_CLIENT_SECRET::"
        },
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:connection_string::"
        },
        {
          name      = "POSTGRES_USER"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:username::"
        },
        {
          name      = "POSTGRES_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:password::"
        },
        {
          name      = "POSTGRES_HOST"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:host::"
        },
        {
          name      = "POSTGRES_PORT"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:port::"
        },
        {
          name      = "POSTGRES_DB"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:database::"
        },
        {
          name      = "REDIS_URL"
          valueFrom = "${aws_secretsmanager_secret.redis.arn}:connection_string::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.beat.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "beat"
        }
      }

      mountPoints = [
        {
          sourceVolume  = "efs-models"
          containerPath = "/mnt/efs/models"
          readOnly      = true
        },
        {
          sourceVolume  = "efs-tenant-data"
          containerPath = "/mnt/efs/tenant-data"
          readOnly      = false
        }
      ]
    }
  ])

  volume {
    name = "efs-models"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.models.id
      transit_encryption = "ENABLED"
      authorization_config {
        iam = "ENABLED"
      }
    }
  }

  volume {
    name = "efs-tenant-data"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.tenant_data.id
      transit_encryption = "ENABLED"
      authorization_config {
        iam = "ENABLED"
      }
    }
  }

  tags = {
    Name   = "${local.tenant_prefix}-beat"
    Tenant = var.tenant_name
  }
}

# ECS Service - Celery Beat
resource "aws_ecs_service" "beat" {
  name            = "${local.tenant_prefix}-beat"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = 1  # Only one beat instance should run
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tenant.id]
    assign_public_ip = false
  }

  deployment_maximum_percent         = 100  # Beat should not have multiple instances
  deployment_minimum_healthy_percent = 0     # Allow taking down the single instance

  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"

  tags = {
    Name   = "${local.tenant_prefix}-beat"
    Tenant = var.tenant_name
  }

  depends_on = [
    aws_iam_role_policy_attachment.ecs_task_execution,
    aws_iam_role_policy.ecs_task_s3,
    aws_iam_role_policy.ecs_task_cloudwatch
  ]
}
