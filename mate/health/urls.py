from django.urls import path

from .views import DetailedHealthCheckView
from .views import HealthCheckView

app_name = "health"

urlpatterns = [
    path("", HealthCheckView.as_view(), name="health"),
    path("detailed/", DetailedHealthCheckView.as_view(), name="health_detailed"),
]

