# ECS Task Definitions for Celery Workers and Beat

# Celery Worker Task Definition
resource "aws_ecs_task_definition" "celery" {
  family                   = "${local.tenant_prefix}-celery"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = local.config.celery_cpu
  memory                  = local.config.celery_memory
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  task_role_arn          = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name  = "celery"
      image = "${var.ecr_repositories["mate-celery"]}:latest"
      
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
          name  = "CELERY_WORKER_QUEUES"
          value = local.config.tier == "enterprise" ? "default,gpu,priority,provisioning,reports,notifications" : "default,reports,notifications"
        },
        {
          name  = "CELERY_WORKER_CONCURRENCY"
          value = local.config.tier == "enterprise" ? "4" : "2"
        },
        {
          name  = "CLOUDWATCH_LOG_GROUP"
          value = aws_cloudwatch_log_group.celery.name
        },
        {
          name  = "CLOUDWATCH_LOG_STREAM"
          value = var.tenant_name
        }
      ]
      
      secrets = [
        {
          name      = "DJANGO_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.django.arn}:DJANGO_SECRET_KEY::"
        },
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:connection_string::"
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
      
      healthCheck = {
        command     = ["CMD-SHELL", "celery -A config.celery_app inspect ping || exit 1"]
        interval    = 60
        timeout     = 10
        retries     = 3
        startPeriod = 120
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
      root_directory     = "/${var.tenant_name}"
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

# Celery Beat Task Definition (scheduler)
resource "aws_ecs_task_definition" "beat" {
  family                   = "${local.tenant_prefix}-beat"
  network_mode            = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                     = 256
  memory                  = 512
  execution_role_arn      = aws_iam_role.ecs_task_execution.arn
  task_role_arn          = aws_iam_role.ecs_task.arn
  
  container_definitions = jsonencode([
    {
      name  = "beat"
      image = "${var.ecr_repositories["mate-beat"]}:latest"
      
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
          name  = "CLOUDWATCH_LOG_GROUP"
          value = aws_cloudwatch_log_group.beat.name
        },
        {
          name  = "CLOUDWATCH_LOG_STREAM"
          value = var.tenant_name
        }
      ]
      
      secrets = [
        {
          name      = "DJANGO_SECRET_KEY"
          valueFrom = "${aws_secretsmanager_secret.django.arn}:DJANGO_SECRET_KEY::"
        },
        {
          name      = "DATABASE_URL"
          valueFrom = "${aws_secretsmanager_secret.db.arn}:connection_string::"
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
    }
  ])
  
  tags = {
    Name   = "${local.tenant_prefix}-beat"
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
    aws_iam_role_policy.ecs_task_s3,
    aws_iam_role_policy.ecs_task_ses
  ]
}

# ECS Service - Celery Beat (only one instance)
resource "aws_ecs_service" "beat" {
  name            = "${local.tenant_prefix}-beat"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = 1  # Always exactly one beat scheduler
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tenant.id]
    assign_public_ip = false
  }
  
  deployment_maximum_percent         = 100  # Only one instance allowed
  deployment_minimum_healthy_percent = 0     # Allow complete replacement
  
  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"
  
  tags = {
    Name   = "${local.tenant_prefix}-beat"
    Tenant = var.tenant_name
  }
  
  depends_on = [
    aws_iam_role_policy.ecs_task_s3,
    aws_iam_role_policy.ecs_task_ses
  ]
}

# Auto-scaling for Django service
resource "aws_appautoscaling_target" "django" {
  count = local.config.enable_autoscaling ? 1 : 0
  
  max_capacity       = local.config.max_capacity
  min_capacity       = local.config.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.django.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "django_cpu" {
  count = local.config.enable_autoscaling ? 1 : 0
  
  name               = "${local.tenant_prefix}-django-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.django[0].resource_id
  scalable_dimension = aws_appautoscaling_target.django[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.django[0].service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    
    target_value = local.config.target_cpu_utilization
  }
}

# Auto-scaling for Celery service
resource "aws_appautoscaling_target" "celery" {
  count = local.config.enable_autoscaling ? 1 : 0
  
  max_capacity       = local.config.max_capacity
  min_capacity       = local.config.min_capacity
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.celery.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "celery_cpu" {
  count = local.config.enable_autoscaling ? 1 : 0
  
  name               = "${local.tenant_prefix}-celery-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.celery[0].resource_id
  scalable_dimension = aws_appautoscaling_target.celery[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.celery[0].service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    
    target_value = local.config.target_cpu_utilization
  }
}