import os

from celery import Celery
from celery.signals import setup_logging
from kombu import Exchange
from kombu import Queue

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("mate")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig  # noqa: PLC0415

    from django.conf import settings  # noqa: PLC0415

    dictConfig(settings.LOGGING)


# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure queue exchanges and bindings
app.conf.task_queues = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("gpu", Exchange("gpu"), routing_key="gpu"),
    Queue("priority", Exchange("priority"), routing_key="priority", priority=10),
    Queue("provisioning", Exchange("provisioning"), routing_key="provisioning"),
    Queue("reports", Exchange("reports"), routing_key="reports"),
    Queue("notifications", Exchange("notifications"), routing_key="notifications"),
)

# Task routing is defined in settings.py
# This allows for environment-specific configurations

