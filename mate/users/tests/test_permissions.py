"""Tests for role-based permissions."""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from mate.tenants.models import Tenant
from mate.tenants.models import TenantUser
from mate.users.permissions import get_user_permissions
from mate.users.permissions import has_permission
from mate.users.permissions import require_hospital_admin
from mate.users.permissions import require_permission
from mate.users.permissions import require_role

User = get_user_model()


@pytest.mark.django_db
class TestPermissions:
    """Test permission functions."""

    @pytest.fixture
    def tenant(self):
        """Create a test tenant."""
        admin_user = User.objects.create_user(
            username="owner",
            email="owner@example.com",
            password="test123!@#",
        )

        return Tenant.objects.create(
            subdomain="test-hospital",
            name="Test Hospital",
            slug="test-hospital",
            deployment_status="active",
            is_active=True,
            owner=admin_user,
            technical_contact_email="tech@test.com",
            billing_contact_email="billing@test.com",
            billing_address="123 Test St",
        )

    def test_get_user_permissions(self, tenant):
        """Test getting permissions for different roles."""
        # Hospital admin
        admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
        )
        admin_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=admin_user,
            role="hospital_admin",
        )

        admin_perms = get_user_permissions(admin_tenant_user)
        assert "manage_users" in admin_perms
        assert "view_billing" in admin_perms

        # Physician
        physician_user = User.objects.create_user(
            username="physician",
            email="physician@example.com",
        )
        physician_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=physician_user,
            role="physician",
        )

        physician_perms = get_user_permissions(physician_tenant_user)
        assert "approve_treatment_plans" in physician_perms
        assert "manage_users" not in physician_perms

        # Student
        student_user = User.objects.create_user(
            username="student",
            email="student@example.com",
        )
        student_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=student_user,
            role="student",
        )

        student_perms = get_user_permissions(student_tenant_user)
        assert "view_patients" in student_perms
        assert "edit_patients" not in student_perms

    def test_has_permission(self, tenant):
        """Test checking specific permissions."""
        physicist_user = User.objects.create_user(
            username="physicist",
            email="physicist@example.com",
        )
        physicist_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=physicist_user,
            role="physicist",
        )

        assert has_permission(physicist_tenant_user, "perform_qa") is True
        assert has_permission(physicist_tenant_user, "sign_reports") is False
        assert has_permission(physicist_tenant_user, "manage_users") is False

    def test_require_permission_decorator(self, tenant):
        """Test require_permission decorator."""
        # Create a mock view function
        @require_permission("manage_users")
        def admin_only_view(request):
            return "Success"

        # Test with admin user
        admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
        )
        admin_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=admin_user,
            role="hospital_admin",
        )

        # Mock request
        request = HttpRequest()
        request.user = admin_user
        request.tenant_user = admin_tenant_user

        # Should work for admin
        result = admin_only_view(request)
        assert result == "Success"

        # Test with regular user
        regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
        )
        regular_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=regular_user,
            role="therapist",
        )

        request.user = regular_user
        request.tenant_user = regular_tenant_user

        # Should raise PermissionDenied
        with pytest.raises(PermissionDenied):
            admin_only_view(request)

    def test_require_role_decorator(self, tenant):
        """Test require_role decorator."""
        # Test single role
        @require_role("physician")
        def physician_view(request):
            return "Physician view"

        # Test multiple roles
        @require_role(["physician", "physicist"])
        def medical_staff_view(request):
            return "Medical staff view"

        # Create users
        physician_user = User.objects.create_user(
            username="physician",
            email="physician@example.com",
        )
        physician_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=physician_user,
            role="physician",
        )

        therapist_user = User.objects.create_user(
            username="therapist",
            email="therapist@example.com",
        )
        therapist_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=therapist_user,
            role="therapist",
        )

        # Mock requests
        physician_request = HttpRequest()
        physician_request.user = physician_user
        physician_request.tenant_user = physician_tenant_user

        therapist_request = HttpRequest()
        therapist_request.user = therapist_user
        therapist_request.tenant_user = therapist_tenant_user

        # Physician can access physician view
        assert physician_view(physician_request) == "Physician view"

        # Therapist cannot
        with pytest.raises(PermissionDenied):
            physician_view(therapist_request)

        # Physician can access medical staff view
        assert medical_staff_view(physician_request) == "Medical staff view"

        # Therapist cannot
        with pytest.raises(PermissionDenied):
            medical_staff_view(therapist_request)

    def test_require_hospital_admin_decorator(self, tenant):
        """Test require_hospital_admin shortcut decorator."""
        @require_hospital_admin
        def admin_view(request):
            return "Admin only"

        # Create admin
        admin_user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
        )
        admin_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=admin_user,
            role="hospital_admin",
        )

        # Create non-admin
        regular_user = User.objects.create_user(
            username="regular",
            email="regular@example.com",
        )
        regular_tenant_user = TenantUser.objects.create(
            tenant=tenant,
            user=regular_user,
            role="physicist",
        )

        # Mock requests
        admin_request = HttpRequest()
        admin_request.user = admin_user
        admin_request.tenant_user = admin_tenant_user

        regular_request = HttpRequest()
        regular_request.user = regular_user
        regular_request.tenant_user = regular_tenant_user

        # Admin can access
        assert admin_view(admin_request) == "Admin only"

        # Non-admin cannot
        with pytest.raises(PermissionDenied):
            admin_view(regular_request)
