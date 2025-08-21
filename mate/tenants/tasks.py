"""
Tenant-aware Celery tasks for HIPAA-compliant background processing
"""
import json
from datetime import timedelta

from celery import Task
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import connection
from django.utils import timezone

from .managers import clear_current_tenant
from .managers import set_current_tenant
from .models import Tenant

logger = get_task_logger(__name__)


class TenantAwareTask(Task):
    """
    Base task class that maintains tenant context across Celery workers
    Ensures all database queries use the correct schema
    """

    def __call__(self, *args, **kwargs):
        """
        Execute task with tenant context
        """
        # Extract tenant_id from kwargs
        tenant_id = kwargs.pop("_tenant_id", None)

        if not tenant_id:
            logger.warning(
                f"Task {self.name} called without tenant context",
            )
            # For some tasks, this might be okay (e.g., system tasks)
            # For others, you might want to raise an exception

        tenant = None
        if tenant_id:
            try:
                # Get tenant and set schema
                tenant = Tenant.objects.get(id=tenant_id)  # type: ignore[attr-defined]
                set_current_tenant(tenant)
                logger.info(
                    f"Task {self.name} running for tenant {tenant.subdomain}",
                )
            except Tenant.DoesNotExist:
                logger.exception(f"Tenant {tenant_id} not found")
                raise

        try:
            # Execute the actual task
            return self.run(*args, **kwargs)
        except Exception as e:
            # Log error with tenant context
            logger.error(
                f"Task {self.name} failed for tenant {tenant.subdomain if tenant else 'none'}: {e!s}",
                exc_info=True,
            )
            raise
        finally:
            # Always reset schema to public
            clear_current_tenant()

    def apply_async(self, args=None, kwargs=None, **options):
        """
        Override to automatically include tenant context and route to tenant-specific queues
        """
        # Get current tenant from thread local
        from .managers import get_current_tenant
        tenant = get_current_tenant()

        if tenant:
            kwargs = kwargs or {}
            kwargs["_tenant_id"] = str(tenant.id)

            # Route to tenant-specific queue in production
            # In local dev, we use shared workers but could use queue prefixes
            if hasattr(settings, "USE_TENANT_QUEUE_ISOLATION") and settings.USE_TENANT_QUEUE_ISOLATION:
                if "queue" in options:
                    # Prefix the queue with tenant subdomain
                    options["queue"] = f"{tenant.subdomain}-{options['queue']}"
                else:
                    # Default to tenant-specific default queue
                    options["queue"] = f"{tenant.subdomain}-default"

                logger.info(f"Routing task {self.name} to queue: {options.get('queue')}")

        return super().apply_async(args, kwargs, **options)


# Tenant-aware task decorator
def tenant_task(**kwargs):
    """
    Decorator to create tenant-aware tasks
    """
    kwargs["base"] = TenantAwareTask
    return shared_task(**kwargs)


# Example tasks

# Example task - replace with your actual app tasks when porting
@tenant_task(name="example_tenant_task")
def example_tenant_task(object_id, options=None):
    """
    Example of a tenant-aware task
    Replace this with your actual business logic when porting apps
    """
    logger.info(f"Processing object {object_id} with tenant isolation")

    # Your task logic here
    # All database queries will automatically be scoped to the tenant

    create_audit_log(
        action="task_completed",
        model_name="ExampleModel",
        object_id=str(object_id),
        details={"options": options},
    )

    return {"status": "success", "object_id": str(object_id)}


@tenant_task(name="generate_report")
def generate_report(report_type, date_range, options=None):
    """
    Generate tenant-specific reports
    """
    logger.info(f"Generating {report_type} report")

    # All queries here will be tenant-scoped
    # Your report generation logic

    create_audit_log(
        action="report_generated",
        model_name="Report",
        object_id=None,
        details={
            "report_type": report_type,
            "date_range": date_range,
            "options": options,
        },
    )

    return {"status": "success", "report_type": report_type}


@tenant_task(name="cleanup_old_files")
def cleanup_old_files(days_to_keep=90):
    """
    Clean up old temporary files
    This is a placeholder - replace with your actual cleanup logic
    """
    timezone.now() - timedelta(days=days_to_keep)

    # Your cleanup logic here
    deleted_count = 0  # Replace with actual cleanup

    logger.info(f"Cleanup task completed - would delete files older than {days_to_keep} days")

    return {"deleted_count": deleted_count}


@shared_task(name="system_health_check")
def system_health_check():
    """
    System-wide health check - runs without tenant context
    """
    results = {}

    # Check each tenant's health
    for tenant in Tenant.objects.filter(is_active=True):  # type: ignore[attr-defined]
        try:
            set_current_tenant(tenant)

            # Run tenant-specific health checks
            with connection.cursor() as cursor:
                # Check schema exists
                cursor.execute(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
                    [tenant.schema_name],
                )
                schema_exists = cursor.fetchone() is not None

                # Check audit log table
                if schema_exists:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {tenant.schema_name}.audit_log",
                    )
                    audit_count = cursor.fetchone()[0]
                else:
                    audit_count = 0

            results[tenant.subdomain] = {
                "status": "healthy" if schema_exists else "error",
                "schema_exists": schema_exists,
                "audit_entries": audit_count,
            }

        except Exception as e:
            logger.exception(f"Health check failed for tenant {tenant.subdomain}: {e!s}")
            results[tenant.subdomain] = {
                "status": "error",
                "error": str(e),
            }
        finally:
            clear_current_tenant()

    return results


@tenant_task(name="send_hipaa_training_reminder")
def send_hipaa_training_reminder():
    """
    Send reminders for HIPAA training renewal
    This is a placeholder - implement when you add notification system
    """
    # Placeholder for HIPAA training reminders
    # Implement when you port your notification system

    logger.info("HIPAA training reminder task - placeholder")

    return {"reminders_sent": 0}


def create_audit_log(action, model_name=None, object_id=None, details=None):
    """
    Helper to create audit log entries in tenant schema
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO audit_log (action, model_name, object_id, changes, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                action,
                model_name,
                object_id,
                json.dumps(details or {}),
                timezone.now(),
            ],
        )


# Periodic task schedules (configured in Django admin with django-celery-beat)
CELERY_BEAT_SCHEDULE = {
    "system-health-check": {
        "task": "system_health_check",
        "schedule": 300.0,  # Every 5 minutes
    },
    "cleanup-temporary-files": {
        "task": "cleanup_old_files",
        "schedule": 86400.0,  # Daily
        "kwargs": {"days_to_keep": 7},
    },
    "hipaa-training-reminders": {
        "task": "send_hipaa_training_reminder",
        "schedule": 86400.0,  # Daily
    },
}
