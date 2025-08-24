from typing import Any

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache


@method_decorator(never_cache, name="dispatch")
class HealthCheckView(View):
    """Basic health check endpoint for monitoring."""

    def get(self, request):
        """Return a simple 200 OK response."""
        return JsonResponse({
            "status": "healthy",
            "service": "mate",
        })


@method_decorator(never_cache, name="dispatch")
class DetailedHealthCheckView(View):
    """Detailed health check that verifies database and cache connectivity."""

    def get(self, request):
        """Check various system components and return their status."""
        health_status: dict[str, Any] = {
            "status": "healthy",
            "service": "mate",
            "checks": {},
        }

        # Check database connectivity
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status["checks"]["database"] = "ok"
        except Exception as e:  # noqa: BLE001
            health_status["checks"]["database"] = f"error: {e!s}"
            health_status["status"] = "unhealthy"

        # Check cache/Redis connectivity
        try:
            cache.set("health_check", "test", 10)
            if cache.get("health_check") == "test":
                health_status["checks"]["cache"] = "ok"
            else:
                health_status["checks"]["cache"] = "error: cache test failed"
                health_status["status"] = "unhealthy"
        except Exception as e:  # noqa: BLE001
            health_status["checks"]["cache"] = f"error: {e!s}"
            health_status["status"] = "unhealthy"

        # Return appropriate status code
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JsonResponse(health_status, status=status_code)

