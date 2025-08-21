"""
Management command to create a hospital admin user for a tenant.
"""
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

from mate.tenants.models import Tenant
from mate.tenants.models import TenantUser
from mate.users.models import User


class Command(BaseCommand):
    help = "Create a hospital admin user for a tenant"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant",
            required=True,
            help="Tenant subdomain",
        )
        parser.add_argument(
            "--email",
            required=True,
            help="Admin user email",
        )
        parser.add_argument(
            "--name",
            required=True,
            help="Admin user full name",
        )
        parser.add_argument(
            "--password",
            help="Password (will generate if not provided)",
        )

    def handle(self, *args, **options):
        try:
            tenant = Tenant.objects.get(subdomain=options["tenant"])
        except Tenant.DoesNotExist:
            msg = f"Tenant '{options['tenant']}' does not exist"
            raise CommandError(msg)

        email = options["email"].lower()

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            msg = f"User with email '{email}' already exists"
            raise CommandError(msg)

        # Check if already in tenant
        if TenantUser.objects.filter(tenant=tenant, user__email=email).exists():
            msg = f"User '{email}' is already in tenant '{tenant.subdomain}'"
            raise CommandError(msg)

        with transaction.atomic():
            # Create user
            user = User.objects.create(
                email=email,
                username=email,
                name=options["name"],
                is_active=True,
                is_staff=True,  # Hospital admins get Django staff access
                auth_method="local",
                force_password_change=True,
            )

            # Set password
            if options["password"]:
                user.set_password(options["password"])
                user.force_password_change = False
            else:
                # Generate password
                import secrets
                import string
                alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                password = "".join(secrets.choice(alphabet) for _ in range(16))
                user.set_password(password)

            user.save()

            # Create tenant association
            TenantUser.objects.create(
                tenant=tenant,
                user=user,
                role="hospital_admin",
                is_active=True,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nHospital admin created successfully!\n"
                    f"Tenant: {tenant.name} ({tenant.subdomain})\n"
                    f"Email: {email}\n"
                    f"Name: {options['name']}\n",
                ),
            )

            if not options["password"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"Temporary password: {password}\n"
                        f"User will be required to change password on first login.",
                    ),
                )

            self.stdout.write(
                f"\nAccess URL: https://{tenant.subdomain}.mate.consensusai.com",
            )

