import secrets
import string

from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from mate.tenants.models import TenantUser

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


# Hospital User Management Forms
class CreateHospitalUserForm(forms.ModelForm):
    """Form for hospital admins to create new users within their tenant."""

    role = forms.ChoiceField(
        choices=[
            ("physician", "Physician"),
            ("physicist", "Physicist"),
            ("dosimetrist", "Dosimetrist"),
            ("therapist", "Therapist"),
            ("resident", "Resident"),
            ("physics_resident", "Physics Resident"),
            ("student", "Student"),
        ],
        initial="therapist",
        help_text=_("Select the user's primary role in the department"),
    )

    auth_method = forms.ChoiceField(
        choices=[
            ("local", "Local Password"),
            ("sso", "Single Sign-On"),
        ],
        initial="local",
        help_text=_("How will this user authenticate?"),
    )

    license_number = forms.CharField(
        required=False,
        help_text=_("Professional license number (if applicable)"),
    )

    supervisor = forms.ModelChoiceField(
        queryset=TenantUser.objects.none(),
        required=False,
        help_text=_("Required for residents and students"),
    )

    send_welcome_email = forms.BooleanField(
        initial=True,
        required=False,
        help_text=_("Send welcome email with login instructions"),
    )

    class Meta:
        model = User
        fields = ["email", "name", "auth_method"]

    def __init__(self, *args, **kwargs):
        self.tenant = kwargs.pop("tenant")
        self.created_by = kwargs.pop("created_by")
        super().__init__(*args, **kwargs)

        # Set supervisor queryset to licensed users in same tenant
        self.fields["supervisor"].queryset = TenantUser.objects.filter(
            tenant=self.tenant,
            role__in=["physician", "physicist", "hospital_admin"],
            is_active=True,
        )

        # If tenant has SSO, make it the default
        if hasattr(self.tenant, "sso_enabled") and self.tenant.sso_enabled:
            self.fields["auth_method"].initial = "sso"
            self.fields["auth_method"].help_text = _(
                "SSO is enabled for your organization. Local passwords should only be used for special cases.",
            )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            # Check if they're already in this tenant
            if TenantUser.objects.filter(
                tenant=self.tenant,
                user__email=email,
            ).exists():
                raise ValidationError(_("This user is already a member of your organization."))
            raise ValidationError(
                _("This email is already registered. They must be added by an administrator."),
            )

        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        supervisor = cleaned_data.get("supervisor")

        # Validate supervisor requirement
        if role in ["resident", "physics_resident", "student"] and not supervisor:
            raise ValidationError({
                "supervisor": _(f"{role.replace('_', ' ').title()}s must have a supervisor assigned."),
            })

        return cleaned_data

    def generate_temp_password(self, length=12):
        """Generate a secure temporary password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def save(self, commit=True):
        """Create user and tenant association."""
        user = super().save(commit=False)

        # Set username to email
        user.username = user.email
        user.created_by = self.created_by

        # Handle authentication method
        auth_method = self.cleaned_data["auth_method"]
        if auth_method == "sso" and hasattr(self.tenant, "sso_enabled") and self.tenant.sso_enabled:
            user.auth_method = "sso"
            user.force_password_change = False
            if commit:
                user.save()
                user.set_unusable_password()
        else:
            user.auth_method = "local"
            temp_password = self.generate_temp_password()
            user.set_password(temp_password)
            # Set force_password_change after set_password since that method resets it
            user.force_password_change = True
            if commit:
                user.save()
            # Store temp password for email
            self.temp_password = temp_password

        if commit:
            # Create tenant user association
            tenant_user = TenantUser.objects.create(
                tenant=self.tenant,
                user=user,
                role=self.cleaned_data["role"],
                license_number=self.cleaned_data.get("license_number", ""),
                supervisor=self.cleaned_data.get("supervisor"),
            )

            # Send welcome email if requested
            if self.cleaned_data.get("send_welcome_email"):
                self.send_welcome_email(user, tenant_user)

        return user

    def send_welcome_email(self, user, tenant_user):
        """Send welcome email to new user."""
        # This would integrate with your email system
        # For now, just a placeholder


class UpdateHospitalUserForm(forms.ModelForm):
    """Form for updating hospital user details."""

    role = forms.ChoiceField(
        choices=[
            ("physician", "Physician"),
            ("physicist", "Physicist"),
            ("dosimetrist", "Dosimetrist"),
            ("therapist", "Therapist"),
            ("resident", "Resident"),
            ("physics_resident", "Physics Resident"),
            ("student", "Student"),
        ],
    )

    license_number = forms.CharField(
        required=False,
        help_text=_("Professional license number (if applicable)"),
    )

    supervisor = forms.ModelChoiceField(
        queryset=TenantUser.objects.none(),
        required=False,
        help_text=_("Required for residents and students"),
    )

    is_active = forms.BooleanField(
        required=False,
        help_text=_("Uncheck to disable user access"),
    )

    class Meta:
        model = User
        fields = ["name", "email"]

    def __init__(self, *args, **kwargs):
        self.tenant_user = kwargs.pop("tenant_user")
        super().__init__(*args, **kwargs)

        # Initialize role field
        self.fields["role"].initial = self.tenant_user.role
        self.fields["license_number"].initial = self.tenant_user.license_number
        self.fields["supervisor"].initial = self.tenant_user.supervisor
        self.fields["is_active"].initial = self.tenant_user.is_active

        # Set supervisor queryset
        self.fields["supervisor"].queryset = TenantUser.objects.filter(
            tenant=self.tenant_user.tenant,
            role__in=["physician", "physicist", "hospital_admin"],
            is_active=True,
        ).exclude(id=self.tenant_user.id)  # Can't supervise yourself

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        supervisor = cleaned_data.get("supervisor")

        # Validate supervisor requirement
        if role in ["resident", "physics_resident", "student"] and not supervisor:
            raise ValidationError({
                "supervisor": _(f"{role.replace('_', ' ').title()}s must have a supervisor assigned."),
            })

        return cleaned_data

    def save(self, commit=True):
        """Update user and tenant association."""
        user = super().save(commit=commit)

        if commit:
            # Update tenant user
            self.tenant_user.role = self.cleaned_data["role"]
            self.tenant_user.license_number = self.cleaned_data.get("license_number", "")
            self.tenant_user.supervisor = self.cleaned_data.get("supervisor")
            self.tenant_user.is_active = self.cleaned_data.get("is_active", True)
            self.tenant_user.save()

        return user


class FirstLoginPasswordChangeForm(forms.Form):
    """Form for users to set their password on first login."""

    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_(
            "Your password must be at least 12 characters long and contain "
            "a mix of uppercase, lowercase, numbers, and symbols.",
        ),
    )

    new_password2 = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")

        # Custom password validation for medical environment
        if len(password) < 12:
            raise ValidationError(_("Password must be at least 12 characters long."))

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not all([has_upper, has_lower, has_digit, has_symbol]):
            raise ValidationError(
                _("Password must contain uppercase, lowercase, numbers, and symbols."),
            )

        # Check against user info
        user_info = [self.user.email, self.user.username, self.user.name]
        for info in user_info:
            if info and info.lower() in password.lower():
                raise ValidationError(
                    _("Password cannot contain your name, email, or username."),
                )

        return password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError(_("The two password fields didn't match."))

        return password2

    def save(self, commit=True):
        """Save the new password."""
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        self.user.force_password_change = False
        if commit:
            self.user.save()
        return self.user

