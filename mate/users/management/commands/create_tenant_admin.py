"""
Management command to create an initial admin user for a tenant.
This is designed to be used during deployment/provisioning.
"""

import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Creates an initial admin user for a tenant with a secure temporary password"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            required=True,
            help="Username for the admin user",
        )
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email address for the admin user",
        )
        parser.add_argument(
            "--tenant",
            type=str,
            help="Tenant identifier (if using multi-tenancy)",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Password for the admin user (auto-generated if not provided)",
        )
        parser.add_argument(
            "--force-password-change",
            action="store_true",
            help="Force password change on first login",
        )
        parser.add_argument(
            "--output-password",
            action="store_true",
            help="Output the generated password (for CI/CD use)",
        )

    def generate_secure_password(self, length=16):
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        tenant = options.get("tenant")
        password = options.get("password")
        force_password_change = options.get("force_password_change", True)
        output_password = options.get("output_password", False)

        # Generate password if not provided
        if not password:
            password = self.generate_secure_password()
            self.stdout.write(
                self.style.WARNING(
                    "Generated temporary password (must be changed on first login)",
                ),
            )

        try:
            with transaction.atomic():
                # Check if user already exists
                if User.objects.filter(username=username).exists():
                    error_msg = f"User '{username}' already exists"
                    raise CommandError(error_msg)  # noqa: TRY301

                # Create the admin user
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                )

                # Set additional attributes
                if hasattr(user, "force_password_change"):
                    user.force_password_change = force_password_change

                if tenant and hasattr(user, "tenant"):
                    user.tenant = tenant

                user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully created admin user '{username}'",
                    ),
                )

                # Output password if requested (for automation)
                if output_password:
                    self.stdout.write(f"PASSWORD={password}")
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "\n" + "=" * 50 + "\n"
                            "IMPORTANT: Save this password securely!\n"
                            f"Username: {username}\n"
                            f"Password: {password}\n"
                            "User will be forced to change password on first login.\n"
                            + "="
                            * 50,
                        ),
                    )

        except Exception as e:
            error_msg = f"Failed to create admin user: {e!s}"
            raise CommandError(error_msg) from e
