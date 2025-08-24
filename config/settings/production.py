# ruff: noqa: E501
import re

# Sentry imports kept for easy switching between CloudWatch and Sentry
from .base import *  # noqa: F403
from .base import BASE_DIR
from .base import DATABASES
from .base import INSTALLED_APPS
from .base import REDIS_URL
from .base import SPECTACULAR_SETTINGS
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY")
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "mate.consensusai.com",
        "localhost",
        "127.0.0.1",
        "10.0.10.100",
        "10.0.20.100",
        "demo.mate.sociant.ai",
        "*",  # Temporarily allow all for debugging
    ],
)

# Tenant configuration from ECS environment
TENANT_SUBDOMAIN = env("TENANT_SUBDOMAIN", default=None)
TENANT_NAME = env("TENANT_NAME", default=None)

# DATABASES
# ------------------------------------------------------------------------------
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

# CACHES
# ------------------------------------------------------------------------------
# ElastiCache Redis is HIPAA-compliant when encryption is enabled
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Mimicking memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True,
            # Enable SSL for ElastiCache encryption in-transit
            "CONNECTION_POOL_KWARGS": {
                "ssl_cert_reqs": "required"
                if REDIS_URL.startswith("rediss://")
                else None,
            },
        },
    },
}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#use-x-forwarded-host
USE_X_FORWARDED_HOST = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-x-forwarded-port
USE_X_FORWARDED_PORT = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-name
SESSION_COOKIE_NAME = "__Secure-sessionid"
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-name
CSRF_COOKIE_NAME = "__Secure-csrftoken"
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-trusted-origins
CSRF_TRUSTED_ORIGINS = [
    "https://demo.mate.sociant.ai",
    "https://mate.consensusai.com",
    "https://*.mate.sociant.ai",  # Allow all subdomains
]
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF",
    default=True,
)


# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
# Use IAM roles in ECS/EC2, otherwise use explicit credentials
AWS_ACCESS_KEY_ID = env("DJANGO_AWS_ACCESS_KEY_ID", default=None)
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_SECRET_ACCESS_KEY = env("DJANGO_AWS_SECRET_ACCESS_KEY", default=None)
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_STORAGE_BUCKET_NAME = env(
    "DJANGO_AWS_STORAGE_BUCKET_NAME",
    default=env("AWS_STORAGE_BUCKET_NAME", default=None),
)
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_QUERYSTRING_AUTH = False
# DO NOT change these unless you know what you're doing.
_AWS_EXPIRY = 60 * 60 * 24 * 7
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": f"max-age={_AWS_EXPIRY}, s-maxage={_AWS_EXPIRY}, must-revalidate",
}
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_S3_MAX_MEMORY_SIZE = env.int(
    "DJANGO_AWS_S3_MAX_MEMORY_SIZE",
    default=100_000_000,  # 100MB
)
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_S3_REGION_NAME = env("DJANGO_AWS_S3_REGION_NAME", default=None)
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#cloudfront
AWS_S3_CUSTOM_DOMAIN = env("DJANGO_AWS_S3_CUSTOM_DOMAIN", default=None)
aws_s3_domain = AWS_S3_CUSTOM_DOMAIN or f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
# STATIC & MEDIA
# ------------------------
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "location": "media",
            "file_overwrite": False,
        },
    },
    "staticfiles": {
        # Use CompressedStaticFilesStorage instead of CompressedManifestStaticFilesStorage
        # to avoid double-hashing Vite's already-hashed files
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
MEDIA_URL = f"https://{aws_s3_domain}/media/"

# WhiteNoise configuration
# ------------------------
# Allow WhiteNoise to serve static files
WHITENOISE_AUTOREFRESH = False
WHITENOISE_USE_FINDERS = False
WHITENOISE_MANIFEST_STRICT = False
# Ensure static files are served from the correct URL
STATIC_URL = "/static/"


# Configure WhiteNoise to recognize Vite's hash pattern as immutable
# This prevents WhiteNoise from adding its own hash to already-hashed Vite files
def immutable_file_test(path, url):
    # Match Vite/Rollup-generated hashes (e.g., main-DGDc5AeB.css)
    # This pattern matches files with 8-12 character hashes before the extension
    return re.match(r"^.+[.-][0-9a-zA-Z_-]{8,12}\..+$", url)


WHITENOISE_IMMUTABLE_FILE_TEST = immutable_file_test

# Skip compression for Vite files as they're already optimized
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = (
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "zip",
    "gz",
    "tgz",
    "bz2",
    "tbz",
    "xz",
    "br",
    "apk",
    "dmg",
    "iso",
    "jar",
    "rar",
    "tar",
    "zip",
    "webm",
    "woff",
    "woff2",
)

# Django Vite configuration
# ------------------------
# Disable Vite dev mode in production - use built static files
DJANGO_VITE = {
    "default": {
        "dev_mode": env.bool(
            "DJANGO_VITE_DEV_MODE",
            default=False,
        ),  # Default to False in production
        "static_url_prefix": "vite",  # Add vite prefix to match the output directory
        "manifest_path": str(BASE_DIR / "staticfiles" / "vite" / "manifest.json"),
    },
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="mate <noreply@mate.consensusai.com>",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[mate] ",
)
ACCOUNT_EMAIL_SUBJECT_PREFIX = EMAIL_SUBJECT_PREFIX

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# Anymail
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ["anymail"]
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
# https://anymail.readthedocs.io/en/stable/esps/amazon_ses/
EMAIL_BACKEND = "anymail.backends.amazon_ses.EmailBackend"
ANYMAIL = {}


# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

# CloudWatch configuration
USE_CLOUDWATCH = env.bool("USE_CLOUDWATCH", default=True)
CLOUDWATCH_LOG_GROUP = env("CLOUDWATCH_LOG_GROUP", default="mate-django")
CLOUDWATCH_LOG_STREAM = env("CLOUDWATCH_LOG_STREAM", default="production")

handlers = {
    "console": {
        "level": "DEBUG",
        "class": "logging.StreamHandler",
        "formatter": "verbose",
    },
}

if USE_CLOUDWATCH:
    # Add CloudWatch handler
    handlers["cloudwatch"] = {
        "level": "INFO",
        "class": "watchtower.CloudWatchLogHandler",
        "log_group": CLOUDWATCH_LOG_GROUP,
        "stream_name": CLOUDWATCH_LOG_STREAM,
        "formatter": "verbose",
        "use_queues": False,  # Set to True for async logging
        "create_log_group": True,
    }
    root_handlers = ["console", "cloudwatch"]
else:
    root_handlers = ["console"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s",
        },
    },
    "handlers": handlers,
    "root": {"level": "INFO", "handlers": root_handlers},
    "loggers": {
        "django.db.backends": {
            "level": "ERROR",
            "handlers": root_handlers,
            "propagate": False,
        },
        # Errors logged by the SDK itself
        "sentry_sdk": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": root_handlers,
            "propagate": False,
        },
        # Application logs
        "mate": {
            "level": "INFO",
            "handlers": root_handlers,
            "propagate": False,
        },
    },
}

# Sentry (Disabled - using CloudWatch instead)
# ------------------------------------------------------------------------------
# Uncomment the following lines if you want to use Sentry instead of CloudWatch
# SENTRY_DSN = env("SENTRY_DSN")
# SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)
#
# sentry_logging = LoggingIntegration(
#     level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
#     event_level=logging.ERROR,  # Send errors as events
# )
# integrations = [
#     sentry_logging,
#     DjangoIntegration(),
#     CeleryIntegration(),
#     RedisIntegration(),
# ]
# sentry_sdk.init(
#     dsn=SENTRY_DSN,
#     integrations=integrations,
#     environment=env("SENTRY_ENVIRONMENT", default="production"),
#     traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
# )

# django-rest-framework
# -------------------------------------------------------------------------------
# Tools that generate code samples can use SERVERS to point to the correct domain
SPECTACULAR_SETTINGS["SERVERS"] = [
    {"url": "https://mate.consensusai.com", "description": "Production server"},
]
# Your stuff...
# ------------------------------------------------------------------------------
# Disable public signup in production
ACCOUNT_ALLOW_REGISTRATION = False
