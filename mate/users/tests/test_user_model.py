"""
Comprehensive tests for the User model.

This module tests all aspects of the User model including:
- Model fields and properties
- Model methods and behaviors
- Relationships and foreign keys
- Model validation
- String representations
"""

from datetime import datetime

import pytest
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from mate.users.models import User
from mate.users.tests.factories import AdminUserFactory
from mate.users.tests.factories import InactiveUserFactory
from mate.users.tests.factories import SSOUserFactory
from mate.users.tests.factories import UserFactory


class UserModelFieldTests(TestCase):
    """Test User model fields and their configurations."""

    def test_user_creation_with_required_fields(self):
        """Test creating a user with only required fields."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.check_password("TestPass123!")
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_user_creation_with_all_fields(self):
        """Test creating a user with all custom fields."""
        admin = AdminUserFactory()
        user = User.objects.create_user(
            username="fulluser",
            email="full@example.com",
            password="Pass123!",
            name="Full User",
            auth_method="sso",
            force_password_change=True,
            created_by=admin,
        )

        assert user.name == "Full User"
        assert user.auth_method == "sso"
        assert user.force_password_change
        assert user.created_by == admin

    def test_name_field_replaces_first_last_name(self):
        """Verify that name field replaces first_name and last_name."""
        user = UserFactory(name="John Doe")

        # name field should be set
        assert user.name == "John Doe"

        # first_name and last_name should be None (as per model definition)
        assert user.first_name is None
        assert user.last_name is None

    def test_auth_method_choices(self):
        """Test auth_method field choices."""
        # Valid choices
        for method in ["local", "sso"]:
            user = UserFactory(auth_method=method)
            user.full_clean()  # Should not raise
            assert user.auth_method == method

        # Invalid choice should raise error
        user = UserFactory()
        user.auth_method = "invalid"
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_password_changed_at_auto_set(self):
        """Test that password_changed_at is automatically set."""
        user = UserFactory()
        assert user.password_changed_at is not None
        assert isinstance(user.password_changed_at, datetime)

    def test_created_by_self_reference(self):
        """Test the self-referential created_by field."""
        admin = AdminUserFactory()
        user1 = UserFactory(created_by=admin)
        user2 = UserFactory(created_by=admin)

        # Check forward relationship
        assert user1.created_by == admin
        assert user2.created_by == admin

        # Check reverse relationship
        created_users = admin.created_users.all()
        assert user1 in created_users
        assert user2 in created_users
        expected_created_users = 2
        assert created_users.count() == expected_created_users

    def test_created_by_null_on_delete(self):
        """Test that created_by is set to NULL when creator is deleted."""
        admin = AdminUserFactory()
        user = UserFactory(created_by=admin)

        # Delete the admin
        admin.delete()

        # Refresh user from database
        user.refresh_from_db()

        # created_by should be None
        assert user.created_by is None


class UserModelMethodTests(TestCase):
    """Test User model methods and properties."""

    def test_get_absolute_url(self):
        """Test the get_absolute_url method."""
        user = UserFactory(username="testuser")
        expected_url = f"/users/{user.username}/"
        assert user.get_absolute_url() == expected_url

    def test_str_representation(self):
        """Test string representation of User model."""
        user = UserFactory(username="john_doe", name="John Doe")

        # __str__ should return username
        assert str(user) == "john_doe"

        # Password should never appear in string representation
        assert "password" not in str(user).lower()

    def test_has_usable_password(self):
        """Test has_usable_password method for different user types."""
        # Local user with password
        local_user = UserFactory(password="TestPass123!")
        assert local_user.has_usable_password()

        # SSO user without password
        sso_user = SSOUserFactory()
        assert not sso_user.has_usable_password()

    def test_check_password_method(self):
        """Test check_password method."""
        user = UserFactory(password="CorrectPass123!")

        # Correct password
        assert user.check_password("CorrectPass123!")

        # Incorrect password
        assert not user.check_password("WrongPassword")

        # Empty password
        assert not user.check_password("")

        # None password
        assert not user.check_password(None)

    def test_set_password_method(self):
        """Test set_password method."""
        user = UserFactory()
        original_password = user.password

        # Set new password
        user.set_password("NewPassword123!")

        # Password should be hashed and different
        assert user.password != "NewPassword123!"  # noqa: S105
        assert user.password != original_password

        # Check it's a Django hash (test env might use md5 for speed)
        assert any(
            user.password.startswith(prefix)
            for prefix in ["pbkdf2_sha256$", "argon2", "bcrypt", "md5$", "sha1$"]
        )

        # Should authenticate with new password
        assert user.check_password("NewPassword123!")

    def test_set_unusable_password(self):
        """Test set_unusable_password method."""
        user = UserFactory(password="TestPass123!")

        # Initially has usable password
        assert user.has_usable_password()

        # Set unusable password
        user.set_unusable_password()

        # Should no longer have usable password
        assert not user.has_usable_password()
        assert not user.check_password("TestPass123!")


class UserModelValidationTests(TestCase):
    """Test User model validation rules."""

    def test_username_required(self):
        """Test that username is required."""
        user = User(email="test@example.com")
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_username_uniqueness(self):
        """Test that username must be unique."""
        UserFactory(username="duplicate")

        # Try to create another user with same username
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username="duplicate",
                email="another@example.com",
                password="Pass123!",
            )

    def test_email_format_validation(self):
        """Test email field format validation."""
        user = UserFactory()

        # Valid email
        user.email = "valid@example.com"
        user.full_clean()  # Should not raise

        # Invalid email
        user.email = "invalid-email"
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_username_max_length(self):
        """Test username maximum length constraint."""
        # Django's default is 150 characters
        long_username = "a" * 150
        user = UserFactory(username=long_username)
        user.full_clean()  # Should not raise

        # Too long
        too_long_username = "a" * 151
        user.username = too_long_username
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_name_field_max_length(self):
        """Test name field maximum length."""
        # Max length is 255 as defined in model
        long_name = "a" * 255
        user = UserFactory(name=long_name)
        user.full_clean()  # Should not raise

        # Too long
        too_long_name = "a" * 256
        user.name = too_long_name
        with pytest.raises(ValidationError):
            user.full_clean()


class UserModelPermissionTests(TestCase):
    """Test User model permissions and authorization."""

    def test_superuser_has_all_permissions(self):
        """Test that superusers have all permissions."""
        admin = AdminUserFactory()

        assert admin.is_superuser
        assert admin.is_staff
        assert admin.has_perm("any.permission")
        assert admin.has_module_perms("any_app")

    def test_regular_user_default_permissions(self):
        """Test regular user default permissions."""
        user = UserFactory()

        assert not user.is_superuser
        assert not user.is_staff
        assert not user.has_perm("some.permission")
        assert not user.has_module_perms("some_app")

    def test_staff_user_permissions(self):
        """Test staff user permissions."""
        staff_user = UserFactory(is_staff=True)

        assert staff_user.is_staff
        assert not staff_user.is_superuser
        # Staff status alone doesn't grant permissions
        assert not staff_user.has_perm("some.permission")

    def test_inactive_user_has_no_permissions(self):
        """Test that inactive users have no permissions."""
        inactive_user = InactiveUserFactory()

        assert not inactive_user.is_active
        assert not inactive_user.has_perm("any.permission")
        assert not inactive_user.has_module_perms("any_app")


class UserModelQuerySetTests(TestCase):
    """Test User model queryset methods and filters."""

    # Test data counts
    NUM_ACTIVE_USERS = 3
    NUM_INACTIVE_USERS = 2
    NUM_ADMIN_USERS = 2
    NUM_SSO_USERS = 2

    def setUp(self):
        """Set up test data."""
        self.active_users = [UserFactory() for _ in range(self.NUM_ACTIVE_USERS)]
        self.inactive_users = [
            InactiveUserFactory() for _ in range(self.NUM_INACTIVE_USERS)
        ]
        self.admin_users = [AdminUserFactory() for _ in range(self.NUM_ADMIN_USERS)]
        self.sso_users = [SSOUserFactory() for _ in range(self.NUM_SSO_USERS)]

    def test_filter_active_users(self):
        """Test filtering active users."""
        active = User.objects.filter(is_active=True)
        inactive = User.objects.filter(is_active=False)

        expected_active = (
            self.NUM_ACTIVE_USERS + self.NUM_ADMIN_USERS + self.NUM_SSO_USERS
        )
        assert active.count() == expected_active
        assert inactive.count() == self.NUM_INACTIVE_USERS

    def test_filter_by_auth_method(self):
        """Test filtering users by authentication method."""
        local_users = User.objects.filter(auth_method="local")
        sso_users = User.objects.filter(auth_method="sso")

        expected_local = (
            self.NUM_ACTIVE_USERS + self.NUM_INACTIVE_USERS + self.NUM_ADMIN_USERS
        )
        assert local_users.count() == expected_local
        assert sso_users.count() == self.NUM_SSO_USERS

    def test_filter_staff_users(self):
        """Test filtering staff users."""
        staff = User.objects.filter(is_staff=True)
        non_staff = User.objects.filter(is_staff=False)

        expected_non_staff = (
            self.NUM_ACTIVE_USERS + self.NUM_INACTIVE_USERS + self.NUM_SSO_USERS
        )
        assert staff.count() == self.NUM_ADMIN_USERS
        assert non_staff.count() == expected_non_staff

    def test_exclude_system_users(self):
        """Test excluding system/service accounts."""
        # If there are system users, they might have specific patterns
        human_users = User.objects.exclude(username__startswith="system_")

        # All our test users should be included
        assert human_users.count() == User.objects.count()


class UserModelIntegrationTests(TestCase):
    """Integration tests for User model with Django auth system."""

    def test_create_user_manager_method(self):
        """Test create_user manager method."""
        user = User.objects.create_user(
            username="newuser",
            email="new@example.com",
            password="Pass123!",
        )

        assert isinstance(user, User)
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
        assert user.check_password("Pass123!")

    def test_create_superuser_manager_method(self):
        """Test create_superuser manager method."""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPass123!",
        )

        assert isinstance(admin, User)
        assert admin.is_active
        assert admin.is_staff
        assert admin.is_superuser
        assert admin.check_password("AdminPass123!")

    def test_user_natural_key(self):
        """Test user natural key for serialization."""
        user = UserFactory(username="testuser")
        natural_key = user.natural_key()

        assert natural_key == ("testuser",)

    def test_user_groups_relationship(self):
        """Test user groups many-to-many relationship."""
        user = UserFactory()
        group1 = Group.objects.create(name="Editors")
        group2 = Group.objects.create(name="Viewers")

        # Add user to groups
        user.groups.add(group1, group2)

        # Check relationships
        assert group1 in user.groups.all()
        assert group2 in user.groups.all()
        num_groups = 2
        assert user.groups.count() == num_groups

    def test_user_permissions_relationship(self):
        """Test user permissions many-to-many relationship."""
        user = UserFactory()

        # Get a permission
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.filter(
            content_type=content_type,
        ).first()

        if permission:
            # Add permission to user
            user.user_permissions.add(permission)

            # Check relationship
            assert permission in user.user_permissions.all()
            perm_name = f"{permission.content_type.app_label}.{permission.codename}"
            assert user.has_perm(perm_name)
