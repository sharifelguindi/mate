"""Tests for user authentication models and methods."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserAuthModel:
    """Test User model authentication features."""

    def test_user_creation_defaults(self):
        """Test user creation with default values."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123!@#",
        )

        assert user.auth_method == "local"
        assert user.force_password_change is False
        assert user.password_changed_at is not None
        assert user.created_by is None

    def test_set_password_updates_timestamp(self):
        """Test that setting password updates password_changed_at."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpass123!@#",
        )

        old_timestamp = user.password_changed_at

        # Wait a bit to ensure timestamp difference
        import time  # noqa: PLC0415

        time.sleep(0.1)

        user.set_password("newpass123!@#")
        user.save()

        assert user.password_changed_at > old_timestamp
        assert user.force_password_change is False

    def test_should_force_password_change(self):
        """Test should_force_password_change method."""
        # Local user with force_password_change=True
        user1 = User.objects.create_user(
            username="localuser",
            email="local@example.com",
            auth_method="local",
            force_password_change=True,
        )
        assert user1.should_force_password_change() is True

        # Local user with force_password_change=False
        user2 = User.objects.create_user(
            username="localuser2",
            email="local2@example.com",
            auth_method="local",
            force_password_change=False,
        )
        assert user2.should_force_password_change() is False

        # SSO user with force_password_change=True (should still be False)
        user3 = User.objects.create_user(
            username="ssouser",
            email="sso@example.com",
            auth_method="sso",
            force_password_change=True,
        )
        assert user3.should_force_password_change() is False

    def test_created_by_relationship(self):
        """Test created_by self-referential relationship."""
        admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123!@#",
        )

        user = User.objects.create_user(
            username="newuser",
            email="new@example.com",
            password="new123!@#",
            created_by=admin,
        )

        assert user.created_by == admin
        assert admin.created_users.count() == 1
        assert admin.created_users.first() == user

    def test_sso_user_unusable_password(self):
        """Test that SSO users can have unusable passwords."""
        user = User.objects.create_user(
            username="ssouser",
            email="sso@example.com",
            auth_method="sso",
        )
        user.set_unusable_password()
        user.save()

        assert not user.has_usable_password()
        assert user.auth_method == "sso"
        assert user.force_password_change is False
