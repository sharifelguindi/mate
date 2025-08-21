"""
Database utilities for dynamic tenant database configuration
"""
import json
import logging

import boto3
from django.conf import settings
from django.db import connections

logger = logging.getLogger("mate.tenants")

# Cache for database configurations to avoid repeated AWS calls
_db_config_cache: dict[str, dict] = {}


def get_tenant_db_config(tenant):
    """
    Get database configuration for a tenant from AWS Secrets Manager
    Results are cached for performance
    """
    cache_key = tenant.subdomain

    # Check cache first
    if cache_key in _db_config_cache:
        return _db_config_cache[cache_key]

    if not tenant.db_secret_arn:
        msg = f"Tenant {tenant.subdomain} has no database secret configured"
        raise ValueError(msg)

    try:
        # Get credentials from AWS Secrets Manager
        secrets_client = boto3.client("secretsmanager", region_name=tenant.aws_region)
        response = secrets_client.get_secret_value(SecretId=tenant.db_secret_arn)
        credentials = json.loads(response["SecretString"])

        db_config = {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": tenant.rds_database_name,
            "USER": credentials.get("username"),
            "PASSWORD": credentials.get("password"),
            "HOST": tenant.rds_endpoint,
            "PORT": str(tenant.rds_port),
            "OPTIONS": {
                "sslmode": "require",
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000",  # 30 second timeout
            },
            "CONN_MAX_AGE": 60,  # Connection pooling
            "ATOMIC_REQUESTS": True,  # Wrap each request in a transaction
        }

        # Cache the configuration
        _db_config_cache[cache_key] = db_config

        return db_config

    except Exception as e:
        logger.exception(f"Failed to get database config for tenant {tenant.subdomain}: {e!s}")
        raise


def configure_tenant_db(tenant):
    """
    Dynamically configure database connection for a tenant
    """
    db_alias = f"tenant_{tenant.subdomain}"

    # Check if already configured
    if db_alias in settings.DATABASES:
        # Database already configured, just ensure connection is valid
        connection = connections[db_alias]
        try:
            connection.ensure_connection()
            return
        except Exception:
            # Connection failed, reconfigure
            logger.info(f"Reconnecting to database for tenant {tenant.subdomain}")

    # Get configuration
    db_config = get_tenant_db_config(tenant)

    # Add to Django's database configuration
    settings.DATABASES[db_alias] = db_config

    # Force Django to create the connection
    connection = connections[db_alias]
    connection.ensure_connection()

    logger.info(f"Configured database connection for tenant {tenant.subdomain}")


def get_redis_config(tenant):
    """
    Get Redis configuration for a tenant from AWS Secrets Manager
    """
    if not tenant.redis_secret_arn:
        msg = f"Tenant {tenant.subdomain} has no Redis secret configured"
        raise ValueError(msg)

    try:
        # Get auth token from AWS Secrets Manager
        secrets_client = boto3.client("secretsmanager", region_name=tenant.aws_region)
        response = secrets_client.get_secret_value(SecretId=tenant.redis_secret_arn)
        credentials = json.loads(response["SecretString"])

        # Build Redis URL
        auth_token = credentials.get("auth_token", "")
        redis_url = f"rediss://:{auth_token}@{tenant.redis_endpoint}:{tenant.redis_port}/0"

        return {
            "url": redis_url,
            "ssl_cert_reqs": "required",
            "ssl_ca_certs": "/opt/certs/redis-ca.pem",
        }

    except Exception as e:
        logger.exception(f"Failed to get Redis config for tenant {tenant.subdomain}: {e!s}")
        raise


def clear_db_config_cache(tenant_subdomain=None):
    """
    Clear cached database configurations
    """
    if tenant_subdomain:
        _db_config_cache.pop(tenant_subdomain, None)
    else:
        _db_config_cache.clear()


def close_tenant_connections():
    """
    Close all tenant database connections
    Useful for cleanup in long-running processes
    """
    for alias in list(connections.databases.keys()):
        if alias.startswith("tenant_"):
            connections[alias].close()

