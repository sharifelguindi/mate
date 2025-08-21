"""Tests for hospital user management forms."""
import pytest
from django.contrib.auth import get_user_model

from mate.tenants.models import Tenant
from mate.tenants.models import TenantUser
from mate.users.forms import CreateHospitalUserForm
from mate.users.forms import FirstLoginPasswordChangeForm
from mate.users.forms import UpdateHospitalUserForm

User = get_user_model()


@pytest.mark.django_db
class TestCreateHospitalUserForm:
    """Test CreateHospitalUserForm."""

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

    @pytest.fixture
    def admin_user(self):
        """Create an admin user."""
        return User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="admin123!@#",
        )

    @pytest.fixture
    def supervisor(self, tenant):
        """Create a supervisor user."""
        user = User.objects.create_user(
            username="supervisor",
            email="supervisor@example.com",
            password="super123!@#",
        )

        TenantUser.objects.create(
            tenant=tenant,
            user=user,
            role="physician",
            is_active=True,
        )

        return user

    def test_valid_form_local_auth(self, tenant, admin_user):
        """Test form with valid local auth data."""
        form_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "auth_method": "local",
            "role": "therapist",
            "send_welcome_email": True,
        }

        form = CreateHospitalUserForm(
            data=form_data,
            tenant=tenant,
            created_by=admin_user,
        )

        assert form.is_valid()

        user = form.save()
        assert user.email == "newuser@example.com"
        assert user.username == "newuser@example.com"
        assert user.auth_method == "local"
        assert user.force_password_change is True
        assert user.created_by == admin_user
        assert hasattr(form, "temp_password")

        # Check tenant association
        tenant_user = TenantUser.objects.get(user=user, tenant=tenant)
        assert tenant_user.role == "therapist"

    def test_valid_form_sso_auth(self, tenant, admin_user):
        """Test form with SSO auth (when SSO not enabled)."""
        form_data = {
            "email": "ssouser@example.com",
            "name": "SSO User",
            "auth_method": "sso",
            "role": "physicist",
            "send_welcome_email": False,
        }

        form = CreateHospitalUserForm(
            data=form_data,
            tenant=tenant,
            created_by=admin_user,
        )

        assert form.is_valid()

        user = form.save()
        # Since tenant doesn't have SSO enabled, should default to local
        assert user.auth_method == "local"
        assert user.force_password_change is True

    def test_supervisor_required_for_resident(self, tenant, admin_user, supervisor):
        """Test that residents require a supervisor."""
        form_data = {
            "email": "resident@example.com",
            "name": "Resident User",
            "auth_method": "local",
            "role": "resident",
            "send_welcome_email": True,
        }

        form = CreateHospitalUserForm(
            data=form_data,
            tenant=tenant,
            created_by=admin_user,
        )

        assert not form.is_valid()
        assert "supervisor" in form.errors

        # Add supervisor and it should work
        supervisor_tenant_user = TenantUser.objects.get(user=supervisor, tenant=tenant)
        form_data["supervisor"] = supervisor_tenant_user.id

        form = CreateHospitalUserForm(
            data=form_data,
            tenant=tenant,
            created_by=admin_user,
        )

        assert form.is_valid()

    def test_duplicate_email_same_tenant(self, tenant, admin_user):
        """Test duplicate email in same tenant."""
        # Create existing user
        existing_user = User.objects.create_user(
            username="existing@example.com",
            email="existing@example.com",
            password="exist123!@#",
        )

        TenantUser.objects.create(
            tenant=tenant,
            user=existing_user,
            role="therapist",
        )

        # Try to create with same email
        form_data = {
            "email": "existing@example.com",
            "name": "Duplicate User",
            "auth_method": "local",
            "role": "therapist",
            "send_welcome_email": True,
        }

        form = CreateHospitalUserForm(
            data=form_data,
            tenant=tenant,
            created_by=admin_user,
        )

        assert not form.is_valid()
        assert "email" in form.errors
        assert "already a member" in str(form.errors["email"])

    def test_email_normalization(self, tenant, admin_user):
        """Test email is normalized to lowercase."""
        form_data = {
            "email": "NewUser@EXAMPLE.com",
            "name": "New User",
            "auth_method": "local",
            "role": "therapist",
            "send_welcome_email": True,
        }

        form = CreateHospitalUserForm(
            data=form_data,
            tenant=tenant,
            created_by=admin_user,
        )

        assert form.is_valid()

        user = form.save()
        assert user.email == "newuser@example.com"
        assert user.username == "newuser@example.com"


@pytest.mark.django_db
class TestFirstLoginPasswordChangeForm:
    """Test FirstLoginPasswordChangeForm."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="old123!@#",
            force_password_change=True,
        )

    def test_valid_password_change(self, user):
        """Test valid password change."""
        form_data = {
            "new_password1": "NewSecure123!@#Pass",
            "new_password2": "NewSecure123!@#Pass",
        }

        form = FirstLoginPasswordChangeForm(user, data=form_data)
        assert form.is_valid()

        form.save()
        user.refresh_from_db()

        assert user.check_password("NewSecure123!@#Pass")
        assert user.force_password_change is False
        assert user.password_changed_at is not None

    def test_password_too_short(self, user):
        """Test password validation - too short."""
        form_data = {
            "new_password1": "Short1!",
            "new_password2": "Short1!",
        }

        form = FirstLoginPasswordChangeForm(user, data=form_data)
        assert not form.is_valid()
        assert "new_password1" in form.errors
        assert "at least 12 characters" in str(form.errors["new_password1"])

    def test_password_missing_requirements(self, user):
        """Test password validation - missing character types."""
        # Missing uppercase
        form_data = {
            "new_password1": "lowercase123!@#",
            "new_password2": "lowercase123!@#",
        }

        form = FirstLoginPasswordChangeForm(user, data=form_data)
        assert not form.is_valid()
        assert "uppercase" in str(form.errors["new_password1"])

    def test_password_contains_user_info(self, user):
        """Test password cannot contain user info."""
        form_data = {
            "new_password1": "test@example.com123!@#ABC",
            "new_password2": "test@example.com123!@#ABC",
        }

        form = FirstLoginPasswordChangeForm(user, data=form_data)
        assert not form.is_valid()
        assert "cannot contain" in str(form.errors["new_password1"])

    def test_password_mismatch(self, user):
        """Test password confirmation mismatch."""
        form_data = {
            "new_password1": "ValidPass123!@#",
            "new_password2": "DifferentPass123!@#",
        }

        form = FirstLoginPasswordChangeForm(user, data=form_data)
        assert not form.is_valid()
        assert "new_password2" in form.errors
        assert "didn&#x27;t match" in str(form.errors["new_password2"])


@pytest.mark.django_db
class TestUpdateHospitalUserForm:
    """Test UpdateHospitalUserForm."""

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

    @pytest.fixture
    def tenant_user(self, tenant):
        """Create a test tenant user."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="test123!@#",
        )

        return TenantUser.objects.create(
            tenant=tenant,
            user=user,
            role="therapist",
            is_active=True,
        )

    def test_update_user_info(self, tenant_user):
        """Test updating user information."""
        form_data = {
            "name": "Updated Name",
            "email": "updated@example.com",
            "role": "dosimetrist",
            "license_number": "DOS-12345",
            "is_active": True,
        }

        form = UpdateHospitalUserForm(
            data=form_data,
            instance=tenant_user.user,
            tenant_user=tenant_user,
        )

        assert form.is_valid()

        user = form.save()
        tenant_user.refresh_from_db()

        assert user.name == "Updated Name"
        assert user.email == "updated@example.com"
        assert tenant_user.role == "dosimetrist"
        assert tenant_user.license_number == "DOS-12345"
        assert tenant_user.is_active is True

    def test_deactivate_user(self, tenant_user):
        """Test deactivating a user."""
        form_data = {
            "name": tenant_user.user.name,
            "email": tenant_user.user.email,
            "role": tenant_user.role,
            "is_active": False,
        }

        form = UpdateHospitalUserForm(
            data=form_data,
            instance=tenant_user.user,
            tenant_user=tenant_user,
        )

        assert form.is_valid()

        form.save()
        tenant_user.refresh_from_db()

        assert tenant_user.is_active is False
