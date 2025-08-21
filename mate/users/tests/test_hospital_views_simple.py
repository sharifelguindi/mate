"""Simplified tests for hospital user management views."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from mate.tenants.models import Tenant
from mate.tenants.models import TenantUser

User = get_user_model()


class TestHospitalUserViewsSimple(TestCase):
    """Test hospital user management views without complex middleware mocking."""

    @classmethod
    def setUpTestData(cls):
        # Create test users
        cls.admin_user = User.objects.create_user(
            username="admin@test.com",
            email="admin@test.com",
            password="testpass123",
        )
        cls.regular_user = User.objects.create_user(
            username="user@test.com",
            email="user@test.com",
            password="testpass123",
        )

        # Give admin user permissions
        cls.admin_user.user_permissions.add(
            Permission.objects.get(codename="view_user"),
            Permission.objects.get(codename="add_user"),
            Permission.objects.get(codename="change_user"),
            Permission.objects.get(codename="delete_user"),
        )

        # Create tenant
        cls.tenant = Tenant.objects.create(
            name="Test Hospital",
            slug="test-hospital",
            subdomain="test-hospital",
            schema_name="test_hospital",
            owner=cls.admin_user,
        )

        # Create tenant users
        cls.admin_tenant_user = TenantUser.objects.create(
            tenant=cls.tenant,
            user=cls.admin_user,
            role="hospital_admin",
            is_active=True,
        )
        cls.regular_tenant_user = TenantUser.objects.create(
            tenant=cls.tenant,
            user=cls.regular_user,
            role="physician",
            is_active=True,
        )

    def test_hospital_user_list_requires_login(self):
        """Test that user list requires authentication."""
        url = reverse("users:hospital-user-list")
        response = self.client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert "redirect" in response.url

    def test_hospital_user_create_requires_login(self):
        """Test that user creation requires authentication."""
        url = reverse("users:hospital-user-create")
        response = self.client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert "redirect" in response.url

    def test_password_change_view_requires_login(self):
        """Test first login password change requires authentication."""
        url = reverse("users:first-login-password-change")
        response = self.client.get(url)

        # Should redirect to login
        assert response.status_code == 302
        assert "/accounts/login/" in response.url

    def test_password_change_post(self):
        """Test password change form submission."""
        # Create a user that needs password change
        user = User.objects.create_user(
            username="newuser@test.com",
            email="newuser@test.com",
            password="temppass123",
        )
        user.force_password_change = True
        user.save()

        # Login
        self.client.login(username="newuser@test.com", password="temppass123")

        # Submit password change
        url = reverse("users:first-login-password-change")
        response = self.client.post(url, {
            "old_password": "temppass123",
            "new_password1": "newSecurePass123!",
            "new_password2": "newSecurePass123!",
        })

        # Should redirect after successful change
        assert response.status_code == 302

        # Check password was changed
        user.refresh_from_db()
        assert not user.force_password_change
        assert user.check_password("newSecurePass123!")
