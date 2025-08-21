from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Default custom user model for mate.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    # Authentication method tracking
    auth_method = models.CharField(
        max_length=20,
        choices=[
            ("local", "Local Password"),
            ("sso", "Single Sign-On"),
        ],
        default="local",
        help_text=_("How this user authenticates"),
    )

    # Password management
    force_password_change = models.BooleanField(
        default=False,
        help_text=_("Force password change on next login"),
    )
    password_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Last password change timestamp"),
    )

    # User creation tracking
    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_users",
        help_text=_("User who created this account"),
    )

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    def set_password(self, raw_password):
        """Override to track password change timestamp."""
        super().set_password(raw_password)
        self.password_changed_at = timezone.now()
        self.force_password_change = False

    def should_force_password_change(self) -> bool:
        """Check if user should be forced to change password."""
        return self.auth_method == "local" and self.force_password_change

    def save(self, *args, **kwargs):
        """Override save to set password_changed_at on creation."""
        if not self.pk and self.password and not self.password_changed_at:
            # New user with password being created
            self.password_changed_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        db_table = "users"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
