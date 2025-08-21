"""
Celery tasks for provisioning tenant infrastructure
"""
import json
import logging

from celery import group
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from mate.tenants.models import Tenant
from mate.tenants.models import TenantEvent
from mate.tenants.models import TenantInfrastructureResource

logger = logging.getLogger("mate.provisioning")


@shared_task(bind=True, max_retries=3)
def provision_tenant_infrastructure(self, tenant_id):
    """
    Main task to provision all infrastructure for a new tenant
    """
    try:
        tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]
        logger.info(f"Starting infrastructure provisioning for tenant: {tenant.subdomain}")

        # Update status
        tenant.infrastructure_status = "provisioning"
        tenant.provisioning_started_at = timezone.now()
        tenant.save()

        # Log event
        TenantEvent.objects.create(  # type: ignore[attr-defined]
            tenant=tenant,
            event_type="provisioning_started",
            details={"task_id": self.request.id},
        )

        # Create infrastructure in parallel where possible
        job = group(
            provision_rds.s(tenant_id),
            provision_s3.s(tenant_id),
            provision_elasticache.s(tenant_id),
            provision_kms.s(tenant_id),
        )
        result = job.apply_async()
        result.get()  # Wait for all to complete

        # After all resources are created, configure them
        configure_tenant_resources.delay(tenant_id)

        return {
            "status": "success",
            "tenant_id": str(tenant_id),
            "message": "Infrastructure provisioning started",
        }

    except Exception as e:
        logger.exception(f"Failed to provision infrastructure for tenant {tenant_id}: {e!s}")

        # Update tenant status
        tenant.infrastructure_status = "failed"
        tenant.save()

        # Log failure event
        TenantEvent.objects.create(  # type: ignore[attr-defined]
            tenant=tenant,
            event_type="infrastructure_failed",
            severity="error",
            details={"error": str(e)},
        )

        # Retry
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))


@shared_task
def provision_rds(tenant_id):
    """
    Provision RDS PostgreSQL instance for tenant
    """
    tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]
    logger.info(f"Provisioning RDS for tenant: {tenant.subdomain}")

    # In production, this would use boto3 or Terraform
    # For now, we'll simulate with boto3
    import boto3

    rds_client = boto3.client("rds", region_name=tenant.aws_region)

    # Generate unique instance identifier
    instance_id = f"mate-{tenant.subdomain}-db"

    try:
        # Create RDS instance
        response = rds_client.create_db_instance(
            DBInstanceIdentifier=instance_id,
            DBInstanceClass="db.t3.medium",
            Engine="postgres",
            EngineVersion="15.3",
            MasterUsername="mate_admin",
            MasterUserPassword=generate_secure_password(),  # Store in Secrets Manager
            DBName=tenant.rds_database_name,
            AllocatedStorage=100,
            StorageEncrypted=True,
            KmsKeyId=tenant.kms_key_arn,  # Use tenant's KMS key
            VpcSecurityGroupIds=[getattr(settings, "RDS_SECURITY_GROUP_ID", "default-rds-sg")],
            DBSubnetGroupName=getattr(settings, "RDS_SUBNET_GROUP_NAME", "default-rds-subnet-group"),
            BackupRetentionPeriod=35,
            PreferredBackupWindow="03:00-04:00",
            MultiAZ=True,
            PubliclyAccessible=False,
            EnableCloudwatchLogsExports=["postgresql"],
            DeletionProtection=True,
            Tags=[
                {"Key": "Tenant", "Value": tenant.subdomain},
                {"Key": "TenantID", "Value": str(tenant.id)},
                {"Key": "Environment", "Value": "production"},
                {"Key": "HIPAA", "Value": "true"},
            ],
        )

        # Store instance details
        tenant.rds_instance_id = instance_id
        tenant.save()

        # Track resource
        TenantInfrastructureResource.objects.create(  # type: ignore[attr-defined]
            tenant=tenant,
            resource_type="rds_instance",
            resource_id=instance_id,
            resource_arn=response["DBInstance"]["DBInstanceArn"],
        )

        logger.info(f"RDS instance created for tenant: {tenant.subdomain}")

    except Exception as e:
        logger.exception(f"Failed to create RDS instance for tenant {tenant.subdomain}: {e!s}")
        raise


@shared_task
def provision_s3(tenant_id):
    """
    Provision S3 bucket for tenant
    """
    tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]
    logger.info(f"Provisioning S3 bucket for tenant: {tenant.subdomain}")

    import boto3

    s3_client = boto3.client("s3", region_name=tenant.aws_region)

    # Generate unique bucket name
    bucket_name = f"mate-{tenant.subdomain}-{generate_random_suffix()}"

    try:
        # Create bucket
        if tenant.aws_region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": tenant.aws_region},
            )

        # Enable versioning
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={"Status": "Enabled"},
        )

        # Enable encryption
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "aws:kms",
                        "KMSMasterKeyID": tenant.kms_key_arn,
                    },
                }],
            },
        )

        # Block public access
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Enable access logging
        s3_client.put_bucket_logging(
            Bucket=bucket_name,
            BucketLoggingStatus={
                "LoggingEnabled": {
                    "TargetBucket": getattr(settings, "S3_LOG_BUCKET", "mate-logs-bucket"),
                    "TargetPrefix": f"access-logs/{tenant.subdomain}/",
                },
            },
        )

        # Add lifecycle policy for HIPAA compliance
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration={
                "Rules": [{
                    "ID": "HIPAA-Retention",
                    "Status": "Enabled",
                    "Transitions": [
                        {
                            "Days": 90,
                            "StorageClass": "STANDARD_IA",
                        },
                        {
                            "Days": 365,
                            "StorageClass": "GLACIER",
                        },
                    ],
                    "NoncurrentVersionTransitions": [
                        {
                            "NoncurrentDays": 30,
                            "StorageClass": "GLACIER",
                        },
                    ],
                }],
            },
        )

        # Store bucket details
        tenant.s3_bucket_name = bucket_name
        tenant.s3_bucket_region = tenant.aws_region
        tenant.save()

        # Track resource
        TenantInfrastructureResource.objects.create(  # type: ignore[attr-defined]
            tenant=tenant,
            resource_type="s3_bucket",
            resource_id=bucket_name,
            resource_arn=f"arn:aws:s3:::{bucket_name}",
        )

        logger.info(f"S3 bucket created for tenant: {tenant.subdomain}")

    except Exception as e:
        logger.exception(f"Failed to create S3 bucket for tenant {tenant.subdomain}: {e!s}")
        raise


@shared_task
def provision_elasticache(tenant_id):
    """
    Provision ElastiCache Redis for tenant
    """
    tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]
    logger.info(f"Provisioning ElastiCache for tenant: {tenant.subdomain}")

    import boto3

    elasticache_client = boto3.client("elasticache", region_name=tenant.aws_region)

    # Generate unique cluster ID
    cluster_id = f"mate-{tenant.subdomain}-redis"

    try:
        # Create ElastiCache cluster
        response = elasticache_client.create_replication_group(
            ReplicationGroupId=cluster_id,
            ReplicationGroupDescription=f"Redis cluster for {tenant.name}",
            Engine="redis",
            EngineVersion="7.0",
            CacheNodeType="cache.t3.micro",  # Start small, can scale later
            NumCacheClusters=1,  # Single node to start
            AtRestEncryptionEnabled=True,
            TransitEncryptionEnabled=True,
            AuthToken=generate_secure_password(),  # Store in Secrets Manager
            CacheSubnetGroupName=getattr(settings, "ELASTICACHE_SUBNET_GROUP_NAME", "default-cache-subnet-group"),
            SecurityGroupIds=[getattr(settings, "ELASTICACHE_SECURITY_GROUP_ID", "default-cache-sg")],
            SnapshotRetentionLimit=7,
            SnapshotWindow="03:00-05:00",
            AutomaticFailoverEnabled=False,  # Enable for Multi-AZ
            Tags=[
                {"Key": "Tenant", "Value": tenant.subdomain},
                {"Key": "TenantID", "Value": str(tenant.id)},
                {"Key": "Environment", "Value": "production"},
                {"Key": "HIPAA", "Value": "true"},
            ],
        )

        # Store cluster details
        tenant.redis_cluster_id = cluster_id
        tenant.save()

        # Track resource
        TenantInfrastructureResource.objects.create(  # type: ignore[attr-defined]
            tenant=tenant,
            resource_type="elasticache_cluster",
            resource_id=cluster_id,
            resource_arn=response["ReplicationGroup"]["ARN"],
        )

        logger.info(f"ElastiCache cluster created for tenant: {tenant.subdomain}")

    except Exception as e:
        logger.exception(f"Failed to create ElastiCache cluster for tenant {tenant.subdomain}: {e!s}")
        raise


@shared_task
def provision_kms(tenant_id):
    """
    Provision KMS key for tenant
    """
    tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]
    logger.info(f"Provisioning KMS key for tenant: {tenant.subdomain}")

    import boto3

    kms_client = boto3.client("kms", region_name=tenant.aws_region)

    try:
        # Create KMS key
        response = kms_client.create_key(
            Description=f"Encryption key for tenant: {tenant.name}",
            KeyUsage="ENCRYPT_DECRYPT",
            Origin="AWS_KMS",
            MultiRegion=False,
            Tags=[
                {"TagKey": "Tenant", "TagValue": tenant.subdomain},
                {"TagKey": "TenantID", "TagValue": str(tenant.id)},
                {"TagKey": "Purpose", "TagValue": "PHI-Encryption"},
            ],
        )

        key_id = response["KeyMetadata"]["KeyId"]
        key_arn = response["KeyMetadata"]["Arn"]

        # Create alias for easier reference
        alias_name = f"alias/mate-{tenant.subdomain}"
        kms_client.create_alias(
            AliasName=alias_name,
            TargetKeyId=key_id,
        )

        # Enable automatic key rotation
        kms_client.enable_key_rotation(KeyId=key_id)

        # Store key details
        tenant.kms_key_id = key_id
        tenant.kms_key_arn = key_arn
        tenant.save()

        # Track resource
        TenantInfrastructureResource.objects.create(  # type: ignore[attr-defined]
            tenant=tenant,
            resource_type="kms_key",
            resource_id=key_id,
            resource_arn=key_arn,
        )

        logger.info(f"KMS key created for tenant: {tenant.subdomain}")

    except Exception as e:
        logger.exception(f"Failed to create KMS key for tenant {tenant.subdomain}: {e!s}")
        raise


@shared_task
def configure_tenant_resources(tenant_id):
    """
    Configure and finalize tenant resources after provisioning
    """
    tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]
    logger.info(f"Configuring resources for tenant: {tenant.subdomain}")

    try:
        # Wait for RDS to be available
        wait_for_rds_available(tenant)

        # Wait for ElastiCache to be available
        wait_for_elasticache_available(tenant)

        # Store credentials in Secrets Manager
        store_tenant_credentials(tenant)

        # Run database migrations
        run_tenant_migrations(tenant)

        # Update tenant status
        tenant.infrastructure_status = "active"
        tenant.is_active = True
        tenant.provisioning_completed_at = timezone.now()
        tenant.activated_at = timezone.now()
        tenant.estimated_monthly_cost = tenant.calculate_estimated_cost()
        tenant.save()

        # Log success event
        TenantEvent.objects.create(  # type: ignore[attr-defined]
            tenant=tenant,
            event_type="provisioning_completed",
            details={
                "duration_minutes": (
                    tenant.provisioning_completed_at - tenant.provisioning_started_at
                ).total_seconds() / 60,
            },
        )

        # Send notification
        send_tenant_ready_notification.delay(tenant_id)

        logger.info(f"Tenant infrastructure ready: {tenant.subdomain}")

    except Exception as e:
        logger.exception(f"Failed to configure resources for tenant {tenant.subdomain}: {e!s}")

        tenant.infrastructure_status = "failed"
        tenant.save()

        raise


@shared_task
def deprovision_tenant_infrastructure(tenant_id):
    """
    Remove all infrastructure for a tenant
    DANGER: This permanently deletes all tenant data!
    """
    tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]

    if tenant.infrastructure_status != "suspended":
        msg = "Tenant must be suspended before deprovisioning"
        raise ValueError(msg)

    # This would delete all AWS resources
    # Implementation depends on your deletion policy


# Utility functions

def generate_secure_password(length=32):
    """Generate a secure random password"""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_random_suffix(length=8):
    """Generate a random suffix for unique resource names"""
    import secrets
    import string
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def wait_for_rds_available(tenant):
    """Wait for RDS instance to be available"""
    import time

    import boto3

    rds_client = boto3.client("rds", region_name=tenant.aws_region)

    for _ in range(60):  # Wait up to 30 minutes
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier=tenant.rds_instance_id,
        )

        instance = response["DBInstances"][0]
        status = instance["DBInstanceStatus"]

        if status == "available":
            # Store endpoint
            tenant.rds_endpoint = instance["Endpoint"]["Address"]
            tenant.save()
            return

        time.sleep(30)

    msg = "RDS instance did not become available in time"
    raise TimeoutError(msg)


def wait_for_elasticache_available(tenant):
    """Wait for ElastiCache cluster to be available"""
    import time

    import boto3

    elasticache_client = boto3.client("elasticache", region_name=tenant.aws_region)

    for _ in range(30):  # Wait up to 15 minutes
        response = elasticache_client.describe_replication_groups(
            ReplicationGroupId=tenant.redis_cluster_id,
        )

        group = response["ReplicationGroups"][0]
        status = group["Status"]

        if status == "available":
            # Store endpoint
            tenant.redis_endpoint = group["NodeGroups"][0]["PrimaryEndpoint"]["Address"]
            tenant.save()
            return

        time.sleep(30)

    msg = "ElastiCache cluster did not become available in time"
    raise TimeoutError(msg)


def store_tenant_credentials(tenant):
    """Store database and Redis credentials in AWS Secrets Manager"""
    import boto3

    secrets_client = boto3.client("secretsmanager", region_name=tenant.aws_region)

    # Store RDS credentials
    db_secret_name = f"mate/{tenant.subdomain}/rds"
    db_secret = {
        "username": "mate_admin",
        "password": generate_secure_password(),
        "engine": "postgres",
        "host": tenant.rds_endpoint,
        "port": tenant.rds_port,
        "dbname": tenant.rds_database_name,
    }

    response = secrets_client.create_secret(
        Name=db_secret_name,
        SecretString=json.dumps(db_secret),
        Tags=[
            {"Key": "Tenant", "Value": tenant.subdomain},
            {"Key": "Type", "Value": "RDS-Credentials"},
        ],
    )

    tenant.db_secret_arn = response["ARN"]

    # Store Redis auth token
    redis_secret_name = f"mate/{tenant.subdomain}/redis"
    redis_secret = {
        "auth_token": generate_secure_password(),
    }

    response = secrets_client.create_secret(
        Name=redis_secret_name,
        SecretString=json.dumps(redis_secret),
        Tags=[
            {"Key": "Tenant", "Value": tenant.subdomain},
            {"Key": "Type", "Value": "Redis-AuthToken"},
        ],
    )

    tenant.redis_secret_arn = response["ARN"]
    tenant.save()


def run_tenant_migrations(tenant):
    """Run Django migrations on tenant database"""
    from django.core.management import call_command

    from mate.tenants.db_utils import configure_tenant_db

    # Configure the database
    configure_tenant_db(tenant)

    # Run migrations
    db_alias = f"tenant_{tenant.subdomain}"
    call_command("migrate", database=db_alias, interactive=False)


@shared_task
def send_tenant_ready_notification(tenant_id):
    """Send notification that tenant is ready"""
    tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]

    # Send email to tenant owner
    # Implementation depends on your notification system
    logger.info(f"Tenant ready notification sent for: {tenant.subdomain}")

