"""Django admin for tenant management.

Only accessible by superusers in production.
"""
from django.contrib import admin

from .models import Tenant
from .models import TenantEvent
from .models import TenantInfrastructureResource
from .models import TenantUsageMetrics
from .models import TenantUser


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "deployment_status",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "deployment_status",
        "is_active",
        "hipaa_compliant",
        "created_at",
    ]
    search_fields = ["name", "slug", "contact_email"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "id",
                "name",
                "slug",
                "schema_name",
                "contact_email",
                "contact_phone",
            ),
        }),
        ("Infrastructure Status", {
            "fields": (
                "deployment_status",
                "is_active",
                "provisioned_at",
            ),
        }),
        ("AWS Resources", {
            "fields": (
                "aws_account_id",
                "vpc_id",
                "subnet_ids",
                "security_group_ids",
                "rds_instance_id",
                "rds_endpoint",
                "elasticache_cluster_id",
                "elasticache_endpoint",
                "s3_bucket_name",
                "kms_key_id",
            ),
            "classes": ("collapse",),
        }),
        ("HIPAA Compliance", {
            "fields": (
                "hipaa_compliant",
                "baa_signed_at",
            ),
        }),
        ("Metadata", {
            "fields": (
                "settings",
                "created_at",
                "updated_at",
            ),
        }),
    )


@admin.register(TenantUser)
class TenantUserAdmin(admin.ModelAdmin):
    list_display = [
        "user_email",
        "tenant_name",
        "role",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "role",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "user__username",
        "tenant__name",
        "tenant__slug",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "last_login_at"]
    raw_id_fields = ["user", "tenant", "supervisor"]

    fieldsets = (
        ("Assignment", {
            "fields": ("tenant", "user", "role", "is_active"),
        }),
        ("Professional Info", {
            "fields": (
                "license_number",
                "specialty",
                "supervisor",
                "certifications",
            ),
        }),
        ("Access Info", {
            "fields": ("last_login_at", "permissions"),
        }),
        ("Metadata", {
            "fields": ("id", "created_at", "updated_at"),
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User"  # type: ignore[attr-defined]
    user_email.admin_order_field = "user__email"  # type: ignore[attr-defined]

    def tenant_name(self, obj):
        return obj.tenant.name
    tenant_name.short_description = "Tenant"  # type: ignore[attr-defined]
    tenant_name.admin_order_field = "tenant__name"  # type: ignore[attr-defined]


@admin.register(TenantEvent)
class TenantEventAdmin(admin.ModelAdmin):
    list_display = [
        "tenant_name",
        "event_type",
        "created_at",
        "user",
    ]
    list_filter = ["event_type", "created_at"]
    search_fields = ["tenant__name", "tenant__slug", "description"]
    readonly_fields = [
        "id",
        "tenant",
        "event_type",
        "user",
        "description",
        "metadata",
        "created_at",
    ]

    def tenant_name(self, obj):
        return obj.tenant.name
    tenant_name.short_description = "Tenant"  # type: ignore[attr-defined]

    def has_add_permission(self, request):
        # Events are created programmatically only
        return False

    def has_change_permission(self, request, obj=None):
        # Events are immutable
        return False

    def has_delete_permission(self, request, obj=None):
        # Events cannot be deleted (audit trail)
        return False


@admin.register(TenantInfrastructureResource)
class TenantInfrastructureResourceAdmin(admin.ModelAdmin):
    list_display = [
        "tenant_name",
        "resource_type",
        "resource_id",
        "status",
        "created_at",
    ]
    list_filter = ["resource_type", "status", "created_at"]
    search_fields = [
        "tenant__name",
        "tenant__slug",
        "resource_id",
        "resource_arn",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["tenant"]

    def tenant_name(self, obj):
        return obj.tenant.name
    tenant_name.short_description = "Tenant"  # type: ignore[attr-defined]


@admin.register(TenantUsageMetrics)
class TenantUsageMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "tenant_name",
        "metric_date",
        "database_storage_gb",
        "s3_storage_gb",
        "api_requests",
        "active_users",
    ]
    list_filter = ["metric_date"]
    search_fields = ["tenant__name", "tenant__slug"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["tenant"]

    def tenant_name(self, obj):
        return obj.tenant.name
    tenant_name.short_description = "Tenant"  # type: ignore[attr-defined]

    def has_add_permission(self, request):
        # Metrics are collected automatically
        return False

    def has_change_permission(self, request, obj=None):
        # Metrics are immutable
        return False

