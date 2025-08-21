"""Role-based permissions for medical team"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

# Define role permissions
ROLE_PERMISSIONS = {
    "hospital_admin": [
        "manage_users",
        "view_all_patients",
        "view_audit_logs",
        "manage_settings",
        "view_billing",
        "manage_tenant",
    ],
    "physician": [
        "view_patients",
        "edit_patients",
        "create_treatment_plans",
        "approve_treatment_plans",
        "sign_reports",
        "order_simulations",
    ],
    "physicist": [
        "view_patients",
        "create_treatment_plans",
        "perform_qa",
        "calibrate_equipment",
        "review_dose_calculations",
        "approve_physics_checks",
    ],
    "dosimetrist": [
        "view_patients",
        "create_treatment_plans",
        "modify_treatment_plans",
        "calculate_dose",
        "export_plans",
    ],
    "therapist": [
        "view_patients",
        "deliver_treatment",
        "record_treatment",
        "capture_images",
        "report_issues",
    ],
    "resident": [
        "view_patients",
        "create_treatment_plans",
        "draft_reports",
        # Limited approval rights
    ],
    "physics_resident": [
        "view_patients",
        "assist_qa",
        "draft_physics_reports",
        "perform_calculations",
        # Learning role with supervision
    ],
    "student": [
        "view_patients",  # Limited/anonymized
        "view_treatment_plans",
        "view_educational_content",
        # Read-only access for learning
    ],
}


def get_user_permissions(tenant_user):
    """Get all permissions for a tenant user based on their role."""
    return ROLE_PERMISSIONS.get(tenant_user.role, [])


def has_permission(tenant_user, permission):
    """Check if a tenant user has a specific permission."""
    permissions = get_user_permissions(tenant_user)
    return permission in permissions


def require_permission(permission):
    """Decorator to require a specific permission."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if not hasattr(request, "tenant_user"):
                msg = "No tenant access"
                raise PermissionDenied(msg)

            if not has_permission(request.tenant_user, permission):
                msg = f"Permission '{permission}' required"
                raise PermissionDenied(msg)

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def require_role(roles):
    """Decorator to require one of the specified roles."""
    if isinstance(roles, str):
        roles = [roles]

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            if not hasattr(request, "tenant_user"):
                msg = "No tenant access"
                raise PermissionDenied(msg)

            if request.tenant_user.role not in roles:
                msg = f"One of these roles required: {', '.join(roles)}"
                raise PermissionDenied(msg)

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def require_hospital_admin(view_func):
    """Shortcut decorator for hospital admin only views."""
    return require_role("hospital_admin")(view_func)


def get_tenant_user_or_403(request):
    """Get tenant user or raise PermissionDenied."""
    if not hasattr(request, "tenant_user"):
        msg = "No tenant access"
        raise PermissionDenied(msg)
    return request.tenant_user

