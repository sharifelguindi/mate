"""
Storage backend for complete tenant isolation
Each tenant has their own S3 bucket
"""
import logging
import os
import uuid
from datetime import datetime

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage

from .managers import get_current_tenant

logger = logging.getLogger("mate.storage")


class TenantS3Storage(S3Boto3Storage):
    """
    S3 storage backend that uses tenant-specific bucket
    Each tenant has complete isolation with their own bucket
    """

    def __init__(self, *args, **kwargs):
        # Don't pass bucket_name to parent __init__
        # We'll set it dynamically based on current tenant
        self._bucket_name = None
        kwargs.pop("bucket_name", None)

        # Force security settings
        kwargs["default_acl"] = "private"
        kwargs["bucket_acl"] = "private"
        kwargs["querystring_auth"] = True
        kwargs["querystring_expire"] = 300  # 5 minutes
        kwargs["file_overwrite"] = False
        kwargs["url_protocol"] = "https:"

        super().__init__(*args, **kwargs)

    @property
    def bucket_name(self):
        """
        Dynamic bucket name based on current tenant
        """
        if self._bucket_name:
            return self._bucket_name

        tenant = get_current_tenant()
        if not tenant:
            msg = "No tenant context for storage operation"
            raise ValueError(msg)

        if not tenant.s3_bucket_name:
            msg = f"Tenant {tenant.subdomain} has no S3 bucket configured"
            raise ValueError(msg)

        return tenant.s3_bucket_name

    @bucket_name.setter
    def bucket_name(self, value):
        """Allow bucket name to be set (for admin/migrations)"""
        self._bucket_name = value

    def get_default_settings(self):
        """
        Get storage settings with tenant-specific encryption
        """
        settings = super().get_default_settings()

        tenant = get_current_tenant()
        if tenant and tenant.kms_key_id:
            # Use tenant-specific KMS key for encryption
            settings.update({
                "encryption": "aws:kms",
                "sse_kms_key_id": tenant.kms_key_arn,
            })
        else:
            # Fall back to S3-managed encryption
            settings["encryption"] = "AES256"

        return settings

    def get_valid_name(self, name):
        """
        Generate safe filenames with timestamp for uniqueness
        Important for medical records to prevent overwrites
        """
        # Get the base name and extension
        base_name, ext = os.path.splitext(name)

        # Clean the base name
        base_name = super().get_valid_name(base_name)

        # Add timestamp and UUID for uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        # Build final filename
        return f"{base_name}_{timestamp}_{unique_id}{ext}"

    def url(self, name):
        """
        Generate signed URLs for all files (required for HIPAA)
        """
        # Always use signed URLs for private buckets
        return self.connection.meta.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": self._encode_name(name),
            },
            ExpiresIn=self.querystring_expire,
        )

    def delete(self, name):
        """
        Override delete to implement soft delete for compliance
        Medical records should not be directly deleted
        """
        tenant = get_current_tenant()

        # Log deletion attempt
        logger.warning(
            f"Deletion attempted for file: {name} in tenant: {tenant.subdomain}",
        )

        # Instead of deleting, you might want to:
        # 1. Move to an archive folder
        # 2. Add deletion marker metadata
        # 3. Schedule for deletion after retention period

        # For now, prevent deletion
        msg = (
            "Direct file deletion is not allowed. "
            "Files must be archived according to retention policy."
        )
        raise NotImplementedError(
            msg,
        )

    def listdir(self, path):
        """
        List directory contents within tenant's bucket only
        """
        # This is already isolated by bucket
        return super().listdir(path)


class SharedEFSStorage:
    """
    Storage for shared ML models and tenant-specific models on EFS
    Models are NOT PHI - no HIPAA concerns for this storage
    """

    EFS_MOUNT_PATH = getattr(settings, "EFS_MOUNT_PATH", "/mnt/efs")

    @classmethod
    def get_model_path(cls, model_name, version=None):
        """
        Get path to ML model file

        Args:
            model_name: Name of the model
            version: Optional version string

        Returns:
            Full path to model file
        """
        if version:
            return os.path.join(
                cls.EFS_MOUNT_PATH,
                "models",
                model_name,
                version,
                "model.pkl",
            )
        return os.path.join(
            cls.EFS_MOUNT_PATH,
            "models",
            model_name,
            "latest",
            "model.pkl",
        )

    @classmethod
    def get_reference_data_path(cls, dataset_name):
        """
        Get path to reference dataset

        Args:
            dataset_name: Name of the dataset

        Returns:
            Full path to dataset
        """
        return os.path.join(
            cls.EFS_MOUNT_PATH,
            "reference-data",
            dataset_name,
        )

    @classmethod
    def list_available_models(cls):
        """
        List all available ML models

        Returns:
            List of model names
        """
        models_dir = os.path.join(cls.EFS_MOUNT_PATH, "models")
        if os.path.exists(models_dir):
            return [
                d for d in os.listdir(models_dir)
                if os.path.isdir(os.path.join(models_dir, d))
            ]
        return []

    @classmethod
    def get_model_versions(cls, model_name):
        """
        Get all versions of a model

        Args:
            model_name: Name of the model

        Returns:
            List of version strings
        """
        model_dir = os.path.join(cls.EFS_MOUNT_PATH, "models", model_name)
        if os.path.exists(model_dir):
            versions = [
                d for d in os.listdir(model_dir)
                if os.path.isdir(os.path.join(model_dir, d)) and d != "latest"
            ]
            return sorted(versions)
        return []

    @classmethod
    def model_exists(cls, model_name, version=None):
        """
        Check if a model exists

        Args:
            model_name: Name of the model
            version: Optional version string

        Returns:
            Boolean indicating if model exists
        """
        model_path = cls.get_model_path(model_name, version)
        return os.path.exists(model_path)

    @classmethod
    def get_tenant_model_path(cls, model_name, version=None):
        """
        Get path to tenant-specific ML model file
        These are models trained by the tenant, NOT PHI data

        Args:
            model_name: Name of the model
            version: Optional version string

        Returns:
            Full path to model file
        """
        tenant = get_current_tenant()
        if not tenant:
            msg = "No tenant context for model storage"
            raise ValueError(msg)

        base_path = os.path.join(
            cls.EFS_MOUNT_PATH,
            "tenant-models",
            tenant.subdomain,
            model_name,
        )

        if version:
            return os.path.join(base_path, version, "model.pkl")
        return os.path.join(base_path, "latest", "model.pkl")

    @classmethod
    def save_tenant_model(cls, model_data, model_name, version=None):
        """
        Save a tenant-specific model to EFS

        Args:
            model_data: The model data (bytes or file-like object)
            model_name: Name of the model
            version: Optional version string (defaults to timestamp)

        Returns:
            Path where model was saved
        """
        import pickle
        from pathlib import Path

        tenant = get_current_tenant()
        if not tenant:
            msg = "No tenant context for model storage"
            raise ValueError(msg)

        # Generate version if not provided
        if not version:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create directory structure
        model_dir = os.path.join(
            cls.EFS_MOUNT_PATH,
            "tenant-models",
            tenant.subdomain,
            model_name,
            version,
        )
        Path(model_dir).mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = os.path.join(model_dir, "model.pkl")

        if hasattr(model_data, "read"):
            # File-like object
            with open(model_path, "wb") as f:
                f.write(model_data.read())
        else:
            # Direct model object
            with open(model_path, "wb") as f:
                pickle.dump(model_data, f)

        # Update latest symlink
        latest_dir = os.path.join(
            cls.EFS_MOUNT_PATH,
            "tenant-models",
            tenant.subdomain,
            model_name,
            "latest",
        )

        # Remove old symlink if exists
        if os.path.exists(latest_dir):
            os.unlink(latest_dir)

        # Create new symlink
        os.symlink(model_dir, latest_dir)

        logger.info(
            f"Saved model {model_name} version {version} for tenant {tenant.subdomain}",
        )

        return model_path

    @classmethod
    def list_tenant_models(cls):
        """
        List all models for current tenant

        Returns:
            List of model names
        """
        tenant = get_current_tenant()
        if not tenant:
            msg = "No tenant context"
            raise ValueError(msg)

        tenant_models_dir = os.path.join(
            cls.EFS_MOUNT_PATH,
            "tenant-models",
            tenant.subdomain,
        )

        if os.path.exists(tenant_models_dir):
            return [
                d for d in os.listdir(tenant_models_dir)
                if os.path.isdir(os.path.join(tenant_models_dir, d))
            ]
        return []


# Utility functions for file organization

def medical_image_upload_path(instance, filename):
    """
    Generate organized upload path for medical images
    Example: medical-images/2024/01/15/mri_brain_20240115_120530_a1b2c3d4.dcm
    """
    date_path = datetime.now().strftime("%Y/%m/%d")

    # Extract metadata from instance if available
    modality = getattr(instance, "modality", "unknown").lower()
    body_part = getattr(instance, "body_part", "unknown").lower()

    # Clean filename
    base_name, ext = os.path.splitext(filename)
    clean_base = "".join(c for c in base_name if c.isalnum() or c in "._- ")[:50]

    # Build organized path
    return f"medical-images/{date_path}/{modality}_{body_part}_{clean_base}{ext}"


def report_upload_path(instance, filename):
    """
    Generate organized upload path for medical reports
    Example: reports/2024/01/patient_12345/radiology_report_20240115.pdf
    """
    date_path = datetime.now().strftime("%Y/%m")
    patient_id = getattr(instance, "patient_id", "unknown")
    report_type = getattr(instance, "report_type", "general").lower()

    base_name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"reports/{date_path}/patient_{patient_id}/{report_type}_{timestamp}{ext}"


def document_upload_path(instance, filename):
    """
    Generate organized upload path for general documents
    Example: documents/2024/01/consent_forms/consent_12345_20240115.pdf
    """
    date_path = datetime.now().strftime("%Y/%m")
    doc_type = getattr(instance, "document_type", "general").lower()

    base_name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]

    return f"documents/{date_path}/{doc_type}/{base_name}_{timestamp}_{unique_id}{ext}"

