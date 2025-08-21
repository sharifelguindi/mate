"""
Management command to set up local test tenants for development.
Creates research-preview and test hospital tenants.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from mate.tenants.models import Tenant
from mate.tenants.models import TenantUser
from mate.users.models import User


class Command(BaseCommand):
    help = "Set up local test tenants for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing test tenants before creating new ones",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Deleting existing test tenants...")
            Tenant.objects.filter(
                subdomain__in=["research-preview", "hospital-test", "memorial"],
            ).delete()
            User.objects.filter(
                email__in=[
                    "admin@research-preview.local",
                    "demo@research-preview.local",
                    "admin@hospital-test.local",
                    "physicist@hospital-test.local",
                    "admin@memorial.local",
                ],
            ).delete()

        with transaction.atomic():
            # Create research-preview tenant
            self.stdout.write("Creating research-preview tenant...")
            self._create_research_preview_tenant()

            # Create test hospital tenant
            self.stdout.write("Creating hospital-test tenant...")
            self._create_test_hospital_tenant()

            # Create a more realistic hospital
            self.stdout.write("Creating Memorial Hospital tenant...")
            self._create_memorial_hospital_tenant()

        self.stdout.write(
            self.style.SUCCESS(
                "\nLocal tenants created successfully!\n\n"
                "Add these to your /etc/hosts file:\n"
                "127.0.0.1 research-preview.localhost\n"
                "127.0.0.1 hospital-test.localhost\n"
                "127.0.0.1 memorial.localhost\n\n"
                "Access URLs:\n"
                "- Research Preview: http://research-preview.localhost:8000\n"
                "- Hospital Test: http://hospital-test.localhost:8000\n"
                "- Memorial Hospital: http://memorial.localhost:8000\n",
            ),
        )

    def _create_research_preview_tenant(self):
        """Create the research preview demo tenant."""
        # Create tenant
        tenant = Tenant.objects.create(
            subdomain="research-preview",
            slug="research-preview",
            name="Research Preview - Demo Access",
            aws_region="us-east-1",

            # Mock infrastructure for local dev
            rds_instance_id="local-research-preview-db",
            rds_endpoint="postgres",
            rds_port=5432,
            rds_database_name="research_preview",

            s3_bucket_name="local-research-preview-bucket",
            s3_bucket_region="us-east-1",

            redis_cluster_id="local-research-preview-redis",
            redis_endpoint="redis",
            redis_port=6379,

            deployment_status="active",
            is_active=True,
            activated_at=timezone.now(),

            plan="starter",
            max_storage_gb=10,
            max_users=20,
            max_api_calls_per_month=10000,

            hipaa_compliant=True,
            data_retention_years=1,  # Short retention for demo

            owner=self._get_or_create_admin_user("admin@research-preview.local"),
            technical_contact_email="admin@research-preview.local",
            billing_contact_email="admin@research-preview.local",
            billing_address="Demo Account - No Billing",
        )

        # Create demo users
        self._create_tenant_user(
            tenant,
            "admin@research-preview.local",
            "Admin User",
            "hospital_admin",
            is_existing=True,
        )

        self._create_tenant_user(
            tenant,
            "demo@research-preview.local",
            "Demo Physician",
            "physician",
        )

        self.stdout.write(
            "  Created research-preview tenant with users:\n"
            "    - admin@research-preview.local (password: admin123!@#)\n"
            "    - demo@research-preview.local (password: demo123!@#)",
        )

        return tenant

    def _create_test_hospital_tenant(self):
        """Create a basic test hospital tenant."""
        # Create tenant
        tenant = Tenant.objects.create(
            subdomain="hospital-test",
            slug="hospital-test",
            name="Test Hospital",
            aws_region="us-east-1",

            # Mock infrastructure
            rds_instance_id="local-hospital-test-db",
            rds_endpoint="postgres",
            rds_port=5432,
            rds_database_name="hospital_test",

            s3_bucket_name="local-hospital-test-bucket",
            s3_bucket_region="us-east-1",

            redis_cluster_id="local-hospital-test-redis",
            redis_endpoint="redis",
            redis_port=6379,

            deployment_status="active",
            is_active=True,
            activated_at=timezone.now(),

            plan="professional",
            max_storage_gb=100,
            max_users=50,

            hipaa_compliant=True,

            owner=self._get_or_create_admin_user("admin@hospital-test.local"),
            technical_contact_email="admin@hospital-test.local",
            billing_contact_email="billing@hospital-test.local",
            billing_address="123 Test St, Test City, TC 12345",
        )

        # Create users
        self._create_tenant_user(
            tenant,
            "admin@hospital-test.local",
            "Test Admin",
            "hospital_admin",
            is_existing=True,
        )

        self._create_tenant_user(
            tenant,
            "physicist@hospital-test.local",
            "Dr. Test Physicist",
            "physicist",
            license_number="PHY-12345",
        )

        self.stdout.write(
            "  Created hospital-test tenant with users:\n"
            "    - admin@hospital-test.local (password: admin123!@#)\n"
            "    - physicist@hospital-test.local (password: test123!@#)",
        )

        return tenant

    def _create_memorial_hospital_tenant(self):
        """Create a realistic hospital with full team."""
        # Create tenant
        tenant = Tenant.objects.create(
            subdomain="memorial",
            slug="memorial",
            name="Memorial Regional Cancer Center",
            aws_region="us-east-1",

            # Mock infrastructure
            rds_instance_id="local-memorial-db",
            rds_endpoint="postgres",
            rds_port=5432,
            rds_database_name="memorial",

            s3_bucket_name="local-memorial-bucket",
            s3_bucket_region="us-east-1",

            redis_cluster_id="local-memorial-redis",
            redis_endpoint="redis",
            redis_port=6379,

            deployment_status="active",
            is_active=True,
            activated_at=timezone.now(),

            plan="enterprise",
            max_storage_gb=1000,
            max_users=200,

            hipaa_compliant=True,
            baa_signed_date=timezone.now().date(),

            owner=self._get_or_create_admin_user("admin@memorial.local"),
            technical_contact_email="it@memorial.local",
            billing_contact_email="billing@memorial.local",
            billing_address="500 Memorial Drive, Metro City, MC 54321",
        )

        # Create realistic team
        self._create_tenant_user(
            tenant,
            "admin@memorial.local",
            "Sarah Johnson",
            "hospital_admin",
            is_existing=True,
        )

        # Physicians
        dr_chen = self._create_tenant_user(
            tenant,
            "mchen@memorial.local",
            "Dr. Michael Chen",
            "physician",
            license_number="MD-98765",
            password="chen123!@#",
        )

        dr_patel = self._create_tenant_user(
            tenant,
            "apatel@memorial.local",
            "Dr. Anjali Patel",
            "physician",
            license_number="MD-87654",
            password="patel123!@#",
        )

        # Physicists
        physicist_wong = self._create_tenant_user(
            tenant,
            "jwong@memorial.local",
            "Dr. James Wong",
            "physicist",
            license_number="PHY-54321",
            password="wong123!@#",
        )

        # Dosimetrist
        self._create_tenant_user(
            tenant,
            "ksmith@memorial.local",
            "Karen Smith",
            "dosimetrist",
            license_number="CMD-11111",
            password="smith123!@#",
        )

        # Therapists
        self._create_tenant_user(
            tenant,
            "rjones@memorial.local",
            "Robert Jones",
            "therapist",
            license_number="RTT-22222",
            password="jones123!@#",
        )

        # Residents (with supervisors)
        self._create_tenant_user(
            tenant,
            "dkim@memorial.local",
            "Dr. David Kim",
            "resident",
            supervisor=dr_chen.user,
            password="kim123!@#",
        )

        self._create_tenant_user(
            tenant,
            "slee@memorial.local",
            "Susan Lee",
            "physics_resident",
            supervisor=physicist_wong.user,
            password="lee123!@#",
        )

        # Student
        self._create_tenant_user(
            tenant,
            "jdoe@memorial.local",
            "Jane Doe",
            "student",
            supervisor=dr_patel.user,
            password="doe123!@#",
        )

        self.stdout.write(
            "  Created Memorial Hospital with full team:\n"
            "    - Admin: admin@memorial.local (admin123!@#)\n"
            "    - Physicians: mchen, apatel\n"
            "    - Physicist: jwong\n"
            "    - Dosimetrist: ksmith\n"
            "    - Therapist: rjones\n"
            "    - Residents: dkim (supervised by Dr. Chen), slee (supervised by Dr. Wong)\n"
            "    - Student: jdoe (supervised by Dr. Patel)\n"
            "    All passwords: [username]123!@#",
        )

        return tenant

    def _get_or_create_admin_user(self, email):
        """Get or create an admin user."""
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "name": "Admin User",
                "is_staff": True,
                "is_active": True,
                "auth_method": "local",
            },
        )

        if created:
            user.set_password("admin123!@#")
            user.save()

        return user

    def _create_tenant_user(
        self,
        tenant,
        email,
        name,
        role,
        license_number="",
        supervisor=None,
        password=None,
        is_existing=False,
    ):
        """Create a user and associate with tenant."""
        if not is_existing:
            user = User.objects.create(
                email=email,
                username=email,
                name=name,
                is_active=True,
                auth_method="local",
            )

            # Set password
            if not password:
                if "admin" in email:
                    password = "admin123!@#"
                elif "demo" in email:
                    password = "demo123!@#"
                else:
                    password = "test123!@#"

            user.set_password(password)
            user.save()
        else:
            user = User.objects.get(email=email)

        # Get supervisor TenantUser if provided
        supervisor_tenant_user = None
        if supervisor:
            supervisor_tenant_user = TenantUser.objects.get(
                tenant=tenant,
                user=supervisor,
            )

        # Create tenant association
        return TenantUser.objects.create(
            tenant=tenant,
            user=user,
            role=role,
            license_number=license_number,
            supervisor=supervisor_tenant_user,
            is_active=True,
        )


