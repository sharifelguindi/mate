"""
Database managers for complete tenant isolation
Each tenant has its own database, no schema switching needed
"""
import logging
import threading

logger = logging.getLogger("mate.tenants")
_thread_locals = threading.local()


def get_current_tenant():
    """Get the current tenant from thread-local storage"""
    return getattr(_thread_locals, "tenant", None)


def set_current_tenant(tenant):
    """Set the current tenant in thread-local storage"""
    _thread_locals.tenant = tenant
    logger.debug(f"Set current tenant to: {tenant.subdomain if tenant else 'None'}")


def clear_current_tenant():
    """Clear the current tenant from thread-local storage"""
    if hasattr(_thread_locals, "tenant"):
        del _thread_locals.tenant
