"""
Example of how to use logging in the application.
Logs will go to CloudWatch in production and console in development.
"""
import logging

from django.db import models

# Get a logger for your module
logger = logging.getLogger(__name__)

# Or use the 'mate' logger for app-specific logs
app_logger = logging.getLogger("mate")


def example_function():
    """Example function showing different log levels."""
    # Debug level - detailed information for diagnosing problems
    logger.debug("This is a debug message - won't show in production")

    # Info level - general informational messages
    logger.info("User performed an action")

    # Warning level - something unexpected happened but app is still working
    logger.warning("API rate limit approaching")

    # Error level - a serious problem occurred
    try:
        _ = 1 / 0
    except ZeroDivisionError:
        logger.exception("Division by zero error occurred")

    # Critical level - a very serious error occurred
    logger.critical("Database connection lost!")

    # Log with extra context
    logger.info(
        "User login successful",
        extra={
            "user_id": 123,
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
        },
    )


# Usage in views
def view_example(request):
    """Example view with logging."""
    logger.info("Request received: %s %s", request.method, request.path)

    try:
        # Your view logic here
        # This is just an example - replace with your actual logic
        result = {"status": "success"}  # Example result
        logger.info("Request processed successfully for user %s", request.user.id)
    except Exception:
        logger.exception(
            "Error processing request for user %s",
            request.user.id,
            extra={"request_id": request.META.get("HTTP_X_REQUEST_ID")},
        )
        raise
    else:
        return result


# Usage in models


class ExampleModel(models.Model):
    """Example model with logging."""

    # Add at least one field for a valid Django model
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        logger.info("Saving %s instance: %s", self.__class__.__name__, self.pk)
        super().save(*args, **kwargs)
        logger.info("Saved %s instance: %s", self.__class__.__name__, self.pk)

