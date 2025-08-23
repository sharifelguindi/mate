from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from django.utils import timezone
from factory import Faker
from factory import LazyAttribute
from factory import LazyFunction
from factory import post_generation
from factory.django import DjangoModelFactory

from mate.users.models import User


class UserFactory(DjangoModelFactory[User]):
    """Base factory for creating User instances with realistic test data."""

    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")

    # Authentication fields
    auth_method = "local"
    is_active = True
    is_staff = False
    is_superuser = False

    # Password management fields
    force_password_change = False
    password_changed_at = LazyFunction(timezone.now)

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):  # noqa: FBT001
        password = (
            extracted
            if extracted
            else Faker(
                "password",
                length=42,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ).evaluate(None, None, extra={"locale": None})
        )
        self.set_password(password)

    @post_generation
    def created_by(self, create: bool, extracted: Any, **kwargs):  # noqa: FBT001
        """Set created_by relationship if specified."""
        if not create:
            return

        if extracted:
            self.created_by = extracted

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results and not cls._meta.skip_postgeneration_save:
            # Some post-generation hooks ran, and may have modified us.
            instance.save()

    class Meta:
        model = User
        django_get_or_create = ["username"]


class AdminUserFactory(UserFactory):
    """Factory for creating admin/superuser accounts."""

    username = Faker("user_name")
    email = LazyAttribute(lambda obj: f"admin_{obj.username}@example.com")
    is_staff = True
    is_superuser = True


class SSOUserFactory(UserFactory):
    """Factory for SSO authenticated users without local passwords."""

    username = Faker("user_name")
    email = LazyAttribute(lambda obj: f"sso_{obj.username}@example.com")
    auth_method = "sso"

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):  # noqa: FBT001
        """SSO users typically don't have local passwords."""
        if not create:
            return
        # Set unusable password for SSO users unless explicitly provided
        if not extracted:
            self.set_unusable_password()
        elif extracted:
            self.set_password(extracted)


class ExpiredPasswordUserFactory(UserFactory):
    """Factory for users with expired passwords requiring change."""

    force_password_change = True
    password_changed_at = LazyFunction(
        lambda: timezone.now() - timedelta(days=91),
    )


class InactiveUserFactory(UserFactory):
    """Factory for inactive/disabled user accounts."""

    is_active = False
    username = Faker("user_name")
    email = LazyAttribute(lambda obj: f"inactive_{obj.username}@example.com")
