from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mate.tenants"
    verbose_name = "Tenants"

    def ready(self):
        # Import signal handlers
        try:
            import mate.tenants.signals  # noqa
        except ImportError:
            pass

