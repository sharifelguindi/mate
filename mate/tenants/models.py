import uuid

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Tenant(models.Model):
    """Multi-tenant organization model with AWS infrastructure."""

    DEPLOYMENT_STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("provisioning", _("Provisioning")),
        ("active", _("Active")),
        ("suspended", _("Suspended")),
        ("terminated", _("Terminated")),
    ]

    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), unique=True, max_length=100)
    subdomain = models.SlugField(_("Subdomain"), unique=True, max_length=100)
    schema_name = models.CharField(
        _("Schema Name"), max_length=63, unique=True, blank=True, null=True,
    )

    # Contact Information
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="owned_tenants",
        null=True,
        blank=True,
    )
    contact_email = models.EmailField(_("Contact Email"), blank=True)
    contact_phone = models.CharField(_("Contact Phone"), max_length=20, blank=True)
    technical_contact_email = models.EmailField(
        _("Technical Contact Email"), blank=True,
    )
    billing_contact_email = models.EmailField(_("Billing Contact Email"), blank=True)
    billing_address = models.TextField(_("Billing Address"), blank=True)

    # AWS Infrastructure
    aws_region = models.CharField(
        _("AWS Region"), max_length=30, default="us-east-1", blank=True,
    )
    aws_account_id = models.CharField(_("AWS Account ID"), max_length=12, blank=True)
    vpc_id = models.CharField(_("VPC ID"), max_length=21, blank=True)
    subnet_ids = ArrayField(
        models.CharField(max_length=24),
        verbose_name=_("Subnet IDs"),
        default=list,
        blank=True,
    )
    security_group_ids = ArrayField(
        models.CharField(max_length=20),
        verbose_name=_("Security Group IDs"),
        default=list,
        blank=True,
    )
    rds_instance_id = models.CharField(_("RDS Instance ID"), max_length=63, blank=True)
    rds_endpoint = models.CharField(_("RDS Endpoint"), max_length=255, blank=True)
    rds_port = models.IntegerField(_("RDS Port"), default=5432)
    rds_database_name = models.CharField(
        _("RDS Database Name"), max_length=63, blank=True,
    )
    elasticache_cluster_id = models.CharField(_("ElastiCache Cluster ID"), max_length=50, blank=True)
    elasticache_endpoint = models.CharField(_("ElastiCache Endpoint"), max_length=255, blank=True)
    redis_cluster_id = models.CharField(
        _("Redis Cluster ID"), max_length=50, blank=True,
    )
    redis_endpoint = models.CharField(_("Redis Endpoint"), max_length=255, blank=True)
    redis_port = models.IntegerField(_("Redis Port"), default=6379)
    s3_bucket_name = models.CharField(_("S3 Bucket Name"), max_length=63, blank=True)
    s3_bucket_region = models.CharField(
        _("S3 Bucket Region"), max_length=30, blank=True,
    )
    kms_key_id = models.CharField(_("KMS Key ID"), max_length=2048, blank=True)
    db_secret_arn = models.CharField(_("DB Secret ARN"), max_length=2048, blank=True)
    redis_secret_arn = models.CharField(
        _("Redis Secret ARN"), max_length=2048, blank=True,
    )

    # Status and Metadata
    deployment_status = models.CharField(
        _("Deployment Status"),
        max_length=20,
        choices=DEPLOYMENT_STATUS_CHOICES,
        default="pending",
    )
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    provisioned_at = models.DateTimeField(_("Provisioned At"), null=True, blank=True)
    activated_at = models.DateTimeField(_("Activated At"), null=True, blank=True)
    provisioning_started_at = models.DateTimeField(
        _("Provisioning Started At"), null=True, blank=True,
    )
    provisioning_completed_at = models.DateTimeField(
        _("Provisioning Completed At"), null=True, blank=True,
    )
    suspended_at = models.DateTimeField(_("Suspended At"), null=True, blank=True)
    is_suspended = models.BooleanField(_("Is Suspended"), default=False)

    # Plan & Billing
    plan = models.CharField(
        _("Plan"),
        max_length=50,
        choices=[
            ("starter", _("Starter")),
            ("professional", _("Professional")),
            ("enterprise", _("Enterprise")),
        ],
        default="starter",
    )
    max_storage_gb = models.IntegerField(_("Max Storage GB"), default=100)
    max_users = models.IntegerField(_("Max Users"), default=50)
    max_api_calls_per_month = models.IntegerField(
        _("Max API Calls per Month"), default=100000,
    )
    estimated_monthly_cost = models.DecimalField(
        _("Estimated Monthly Cost"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # HIPAA Compliance
    hipaa_compliant = models.BooleanField(_("HIPAA Compliant"), default=False)
    is_hipaa_compliant = models.BooleanField(_("Is HIPAA Compliant"), default=False)
    baa_signed_at = models.DateTimeField(_("BAA Signed At"), null=True, blank=True)
    baa_signed_date = models.DateField(_("BAA Signed Date"), null=True, blank=True)
    baa_document = models.FileField(
        _("BAA Document"), upload_to="baa_documents/", null=True, blank=True,
    )
    data_retention_years = models.IntegerField(_("Data Retention Years"), default=7)

    # Configuration
    settings = models.JSONField(_("Settings"), default=dict, blank=True)

    class Meta:
        verbose_name = _("Tenant")
        verbose_name_plural = _("Tenants")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_database_name(self):
        """Return the database name for this tenant."""
        return f"tenant_{self.schema_name}"


class TenantUser(models.Model):
    """User association with tenant including medical roles."""

    ROLE_CHOICES = [
        # Administrative roles
        ("hospital_admin", _("Hospital Administrator")),

        # Medical professionals
        ("physician", _("Physician")),
        ("physicist", _("Medical Physicist")),
        ("dosimetrist", _("Dosimetrist")),
        ("therapist", _("Radiation Therapist")),

        # Training roles
        ("resident", _("Resident")),
        ("physics_resident", _("Physics Resident")),
        ("student", _("Student")),
    ]

    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="tenant_users",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tenant_memberships",
    )
    role = models.CharField(_("Role"), max_length=50, choices=ROLE_CHOICES)

    # Professional information
    license_number = models.CharField(
        _("License Number"),
        max_length=50,
        blank=True,
        help_text=_("Professional license number"),
    )
    specialty = models.CharField(
        _("Specialty"),
        max_length=100,
        blank=True,
        help_text=_("Medical specialty or area of expertise"),
    )
    supervisor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supervisees",
        help_text=_("Supervising physician or physicist for residents/students"),
    )
    certifications = ArrayField(
        models.CharField(max_length=100),
        verbose_name=_("Certifications"),
        default=list,
        blank=True,
        help_text=_("Professional certifications (e.g., ABR, ABMS)"),
    )

    # Permissions and status
    is_active = models.BooleanField(_("Is Active"), default=True)
    permissions = models.JSONField(_("Permissions"), default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    last_login_at = models.DateTimeField(_("Last Login At"), null=True, blank=True)

    class Meta:
        verbose_name = _("Tenant User")
        verbose_name_plural = _("Tenant Users")
        unique_together = [["tenant", "user"]]
        ordering = ["tenant", "user"]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.tenant.name} ({self.get_role_display()})"

    def has_permission(self, permission):
        """Check if user has a specific permission within the tenant."""
        return self.permissions.get(permission, False)

    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login_at"])


class TenantInfrastructureResource(models.Model):
    """Track individual AWS resources for a tenant."""

    RESOURCE_TYPE_CHOICES = [
        ("vpc", _("VPC")),
        ("subnet", _("Subnet")),
        ("security_group", _("Security Group")),
        ("rds_instance", _("RDS Instance")),
        ("elasticache_cluster", _("ElastiCache Cluster")),
        ("s3_bucket", _("S3 Bucket")),
        ("kms_key", _("KMS Key")),
        ("iam_role", _("IAM Role")),
        ("iam_policy", _("IAM Policy")),
        ("lambda_function", _("Lambda Function")),
        ("cloudwatch_log_group", _("CloudWatch Log Group")),
    ]

    STATUS_CHOICES = [
        ("creating", _("Creating")),
        ("active", _("Active")),
        ("updating", _("Updating")),
        ("deleting", _("Deleting")),
        ("deleted", _("Deleted")),
        ("failed", _("Failed")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="infrastructure_resources",
    )
    resource_type = models.CharField(
        _("Resource Type"),
        max_length=50,
        choices=RESOURCE_TYPE_CHOICES,
    )
    resource_id = models.CharField(_("Resource ID"), max_length=255)
    resource_arn = models.CharField(_("Resource ARN"), max_length=2048, blank=True)
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default="creating",
    )
    configuration = models.JSONField(_("Configuration"), default=dict, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Infrastructure Resource")
        verbose_name_plural = _("Infrastructure Resources")
        ordering = ["tenant", "resource_type", "created_at"]
        indexes = [
            models.Index(fields=["tenant", "resource_type"]),
            models.Index(fields=["resource_id"]),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.get_resource_type_display()} - {self.resource_id}"


class TenantEvent(models.Model):
    """Audit log for tenant-related events."""

    EVENT_TYPE_CHOICES = [
        ("created", _("Created")),
        ("updated", _("Updated")),
        ("provisioned", _("Provisioned")),
        ("suspended", _("Suspended")),
        ("reactivated", _("Reactivated")),
        ("terminated", _("Terminated")),
        ("user_added", _("User Added")),
        ("user_removed", _("User Removed")),
        ("user_role_changed", _("User Role Changed")),
        ("resource_created", _("Resource Created")),
        ("resource_deleted", _("Resource Deleted")),
        ("backup_created", _("Backup Created")),
        ("backup_restored", _("Backup Restored")),
        ("error", _("Error")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="events",
    )
    event_type = models.CharField(
        _("Event Type"),
        max_length=50,
        choices=EVENT_TYPE_CHOICES,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tenant_events",
    )
    description = models.TextField(_("Description"))
    metadata = models.JSONField(_("Metadata"), default=dict, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        verbose_name = _("Tenant Event")
        verbose_name_plural = _("Tenant Events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.get_event_type_display()} - {self.created_at}"


class TenantUsageMetrics(models.Model):
    """Track resource usage metrics for billing and monitoring."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="usage_metrics",
    )
    metric_date = models.DateField(_("Metric Date"))

    # Storage metrics (in GB)
    database_storage_gb = models.DecimalField(
        _("Database Storage (GB)"),
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    s3_storage_gb = models.DecimalField(
        _("S3 Storage (GB)"),
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # Compute metrics
    compute_hours = models.DecimalField(
        _("Compute Hours"),
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # User metrics
    active_users = models.IntegerField(_("Active Users"), default=0)
    total_logins = models.IntegerField(_("Total Logins"), default=0)

    # API metrics
    api_requests = models.IntegerField(_("API Requests"), default=0)

    # Bandwidth (in GB)
    data_transfer_in_gb = models.DecimalField(
        _("Data Transfer In (GB)"),
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    data_transfer_out_gb = models.DecimalField(
        _("Data Transfer Out (GB)"),
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    # Timestamps
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        verbose_name = _("Usage Metric")
        verbose_name_plural = _("Usage Metrics")
        unique_together = [["tenant", "metric_date"]]
        ordering = ["tenant", "-metric_date"]
        indexes = [
            models.Index(fields=["tenant", "-metric_date"]),
        ]

    def __str__(self):
        return f"{self.tenant.name} - {self.metric_date}"

