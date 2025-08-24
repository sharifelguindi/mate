from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from mate.health.views import HealthCheckView
from mate.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)


app_name = "api"
urlpatterns = [
    # API health check endpoint
    path("v1/health/", HealthCheckView.as_view(), name="api_health"),
    *router.urls,
]
