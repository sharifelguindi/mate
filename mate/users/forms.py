from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    error_messages = {"duplicate_username": _("This username has already been taken.")}

    class Meta(admin_forms.AdminUserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        fields = (*admin_forms.AdminUserCreationForm.Meta.fields, "email", "groups")
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


class FirstLoginPasswordChangeForm(forms.Form):
    """Form for users to change password on first login."""

    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
        help_text=_(
            "Your password must contain at least 12 characters, "
            "including uppercase, lowercase, numbers, and special characters.",
        ),
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")

        # Custom password validation for medical environment
        min_password_length = 12
        if len(password) < min_password_length:
            raise ValidationError(_("Password must be at least 12 characters long."))

        if not any(c.isupper() for c in password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
            )

        if not any(c.islower() for c in password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
            )

        if not any(c.isdigit() for c in password):
            raise ValidationError(_("Password must contain at least one number."))

        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            raise ValidationError(
                _("Password must contain at least one special character."),
            )

        return password

    def clean_new_password2(self):
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password2:
            if password1 != password2:
                raise ValidationError(
                    _("The two password fields didn't match."),
                    code="password_mismatch",
                )
        return password2

    def save(self, commit=True):  # noqa: FBT002
        """Save the new password."""
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        self.user.force_password_change = False
        if commit:
            self.user.save()
        return self.user
