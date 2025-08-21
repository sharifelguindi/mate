"""
Task Routing Demo - Shows exactly how tasks are routed in different environments
Run this in Django shell to see the routing in action
"""

from django.conf import settings

from mate.tenants.managers import get_current_tenant
from mate.tenants.managers import set_current_tenant
from mate.tenants.models import Tenant
from mate.tenants.tasks import tenant_task


# Example task definition
@tenant_task(name="demo_task")
def process_patient_data(patient_id, processing_type="standard"):
    """Demo task that would process patient data"""
    tenant = get_current_tenant()
    print(f"Processing patient {patient_id} for tenant {tenant.subdomain if tenant else 'none'}")
    return f"Processed {patient_id}"


def demonstrate_task_routing():
    """
    Demonstrates how tasks are routed differently in local vs production
    """

    # Simulate having a tenant context (normally set by middleware)
    tenant = Tenant.objects.first()  # Get hospital-a
    set_current_tenant(tenant)

    print("=== TASK ROUTING DEMONSTRATION ===")
    print(f"Current Tenant: {tenant.subdomain}")
    print(f"Tenant ID: {tenant.id}")
    print(f"USE_TENANT_QUEUE_ISOLATION: {getattr(settings, 'USE_TENANT_QUEUE_ISOLATION', False)}")
    print()

    # 1. Standard task call
    print("1. Standard task call:")
    print("   Code: process_patient_data.delay(patient_id=123)")

    # Show what happens internally

    # Mock the apply_async to show routing
    task = process_patient_data
    kwargs = {"patient_id": 123}
    options = {}

    # This is what happens inside TenantAwareTask.apply_async
    print("\n   Inside TenantAwareTask.apply_async:")
    print(f"   - Current tenant detected: {tenant.subdomain}")
    print(f"   - Adding _tenant_id to kwargs: {tenant.id}")

    kwargs["_tenant_id"] = str(tenant.id)

    if getattr(settings, "USE_TENANT_QUEUE_ISOLATION", False):
        # Production behavior
        default_queue = f"{tenant.subdomain}-default"
        print(f"   - Production mode: Routing to queue '{default_queue}'")
        print(f"   - Task will be sent to: redis://{tenant.subdomain}-redis.cache.amazonaws.com:6379")
    else:
        # Local behavior
        print("   - Local mode: Using shared queue 'default'")
        print("   - Task will be sent to: redis://localhost:6379")

    print("\n2. GPU task with explicit queue:")
    print("   Code: process_medical_image.apply_async(args=[456], queue='gpu')")

    options = {"queue": "gpu"}
    if getattr(settings, "USE_TENANT_QUEUE_ISOLATION", False):
        gpu_queue = f"{tenant.subdomain}-gpu"
        print(f"   - Production: Queue 'gpu' becomes '{gpu_queue}'")
    else:
        print("   - Local: Queue remains 'gpu' (shared)")

    print("\n3. Priority task example:")
    print("   Code: send_emergency_alert.apply_async(args=[789], queue='priority')")

    options = {"queue": "priority"}
    if getattr(settings, "USE_TENANT_QUEUE_ISOLATION", False):
        priority_queue = f"{tenant.subdomain}-priority"
        print(f"   - Production: Routed to '{priority_queue}' queue")
        print(f"   - Only {tenant.subdomain}'s priority workers will see this task")
    else:
        print("   - Local: Routed to shared 'priority' queue")
        print("   - Any priority worker can pick this up")

    print("\n=== WORKER SIDE ===")
    print("\nWhen a worker picks up the task:")
    print("1. Extracts _tenant_id from task kwargs")
    print("2. Loads tenant from database")
    print("3. Sets current schema to tenant's schema")
    print("4. All database queries now use tenant's isolated schema")
    print("5. After task completion, resets schema to public")

    print("\n=== LOCAL vs PRODUCTION INFRASTRUCTURE ===")

    print("\nLocal Docker Compose:")
    print("- 1 Redis instance (shared)")
    print("- 4 worker types (shared):")
    print("  - celeryworker (default queues)")
    print("  - celeryworker-gpu")
    print("  - celeryworker-priority")
    print("  - celeryworker-provisioning")

    print("\nProduction Kubernetes (per tenant):")
    print(f"- Namespace: tenant-{tenant.subdomain}")
    print(f"- Redis: {tenant.subdomain}-redis.cache.amazonaws.com")
    print("- Workers:")
    print(f"  - {tenant.subdomain}-default-worker (4 replicas)")
    print(f"  - {tenant.subdomain}-gpu-worker (1 replica)")
    print(f"  - {tenant.subdomain}-priority-worker (2 replicas)")
    print(f"  - {tenant.subdomain}-provisioning-worker (1 replica)")


def show_actual_task_routing():
    """
    Shows the actual result of task routing
    """
    from celery import current_app

    print("\n=== ACTUAL CELERY CONFIGURATION ===")
    print(f"Broker URL: {current_app.conf.broker_url}")
    print(f"Result Backend: {current_app.conf.result_backend}")

    print("\nConfigured Queues:")
    for queue in current_app.conf.task_queues:
        print(f"- {queue.name} (exchange: {queue.exchange.name})")

    print("\nTask Routes:")
    routes = current_app.conf.task_routes or {}
    for pattern, route in routes.items():
        print(f"- {pattern} -> {route}")


if __name__ == "__main__":
    # This would be run in Django shell
    demonstrate_task_routing()
    show_actual_task_routing()
