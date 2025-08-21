"""
Middleware for tenant detection in AWS-native multi-tenant architecture.
Each tenant has isolated AWS resources (RDS, S3, ElastiCache).
"""
import logging
import os

from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

from .models import Tenant
from .models import TenantUser

logger = logging.getLogger("mate.tenants")


class TenantMiddleware(MiddlewareMixin):
    """
    Middleware for AWS-native multi-tenant architecture:
    1. Identify tenant from request (subdomain or header)
    2. Validate tenant is active in ECS deployment
    3. Validate user access to tenant
    4. Set up tenant context for the request

    Note: Each tenant has their own ECS service, so database/Redis
    connections are already configured via environment variables.
    """

    def process_request(self, request):
        """Process incoming request to set tenant context"""
        # Try to get tenant from request
        tenant = self.get_tenant(request)

        if tenant:
            # Validate tenant is active
            if not tenant.is_active:
                logger.warning(f"Access attempt to inactive tenant: {tenant.subdomain}")
                msg = "This organization's account is currently inactive"
                raise Http404(msg)

            # Check deployment status for AWS infrastructure
            if tenant.deployment_status != "active":
                logger.warning(f"Access attempt to tenant with status {tenant.deployment_status}: {tenant.subdomain}")
                if tenant.deployment_status == "provisioning":
                    msg = "Your environment is being set up. Please try again in a few minutes."
                elif tenant.deployment_status == "suspended":
                    msg = "This organization's account has been suspended"
                else:
                    msg = "This organization is not available"
                raise Http404(msg)

            # Set tenant on request
            request.tenant = tenant

            # Validate user access if authenticated
            if request.user.is_authenticated:
                self.validate_user_access(request, tenant)

            # Log tenant access for monitoring
            logger.info(f"Tenant access: {tenant.subdomain} by user: {request.user if request.user.is_authenticated else 'anonymous'}")
        else:
            # No tenant - this is fine for public pages or management interface
            request.tenant = None

    def process_response(self, request, response):
        """Add tenant headers to response for monitoring"""
        if hasattr(request, "tenant") and request.tenant:
            response["X-Tenant-ID"] = str(request.tenant.id)
            response["X-Tenant-Name"] = request.tenant.subdomain
        return response

    def process_exception(self, request, exception):
        """Log exceptions with tenant context"""
        if hasattr(request, "tenant") and request.tenant:
            logger.error(f"Exception in tenant {request.tenant.subdomain}: {exception}")

    def get_tenant(self, request):
        """
        Identify tenant from request.
        In ECS deployment, tenant is determined by:
        1. Environment variable (each ECS service has TENANT_SUBDOMAIN set)
        2. Header (for API requests)
        3. Subdomain (for web requests)
        """
        # 1. Check environment variable (primary method in ECS)
        env_tenant = os.environ.get("TENANT_SUBDOMAIN")
        if env_tenant:
            try:
                return Tenant.objects.get(
                    subdomain=env_tenant,
                    is_active=True,
                    deployment_status="active",
                )
            except Tenant.DoesNotExist:
                logger.exception(f"Tenant from environment not found: {env_tenant}")
                # This is a critical error - the ECS service is misconfigured
                msg = "Service configuration error"
                raise Http404(msg)

        # 2. Check header (for API requests to shared management service)
        tenant_id = request.META.get("HTTP_X_TENANT_ID")
        if tenant_id:
            try:
                return Tenant.objects.get(
                    id=tenant_id,
                    is_active=True,
                    deployment_status="active",
                )
            except Tenant.DoesNotExist:
                logger.warning(f"Invalid tenant ID in header: {tenant_id}")
                msg = "Tenant not found"
                raise Http404(msg)

        # 3. Check subdomain (for development or shared services)
        host = request.get_host().split(":")[0].lower()

        # Skip if localhost or IP
        if host in ["localhost", "127.0.0.1"] or "." not in host:
            # For local development, check session
            if hasattr(request, "session") and "tenant_id" in request.session:
                try:
                    return Tenant.objects.get(
                        id=request.session["tenant_id"],
                        is_active=True,
                        deployment_status="active",
                    )
                except Tenant.DoesNotExist:
                    pass
            return None

        # Extract subdomain
        parts = host.split(".")
        if len(parts) >= 3:  # subdomain.domain.com
            subdomain = parts[0]

            # Skip www and other system subdomains
            if subdomain in ["www", "api", "admin", "docs", "manage"]:
                return None

            try:
                return Tenant.objects.get(
                    subdomain=subdomain,
                    is_active=True,
                    deployment_status="active",
                )
            except Tenant.DoesNotExist:
                logger.warning(f"Unknown subdomain: {subdomain}")
                msg = "Organization not found"
                raise Http404(msg)

        return None

    def validate_user_access(self, request, tenant):
        """Validate user has access to this tenant"""
        try:
            tenant_user = TenantUser.objects.get(
                tenant=tenant,
                user=request.user,
                is_active=True,
            )

            # Check HIPAA compliance requirements
            if tenant.hipaa_compliant:
                # Log for audit trail
                logger.info(
                    f"HIPAA-compliant access: user={request.user.email}, "
                    f"tenant={tenant.subdomain}, role={tenant_user.role}",
                )

            # Update last login
            tenant_user.update_last_login()

            # Add tenant user to request for use in views
            request.tenant_user = tenant_user

        except TenantUser.DoesNotExist:
            # User is authenticated but not a member of this tenant
            logger.warning(
                f"Unauthorized tenant access attempt: "
                f"user={request.user.email}, tenant={tenant.subdomain}",
            )
            msg = "You don't have access to this organization"
            raise Http404(msg)

