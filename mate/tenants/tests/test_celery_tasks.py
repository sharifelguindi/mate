"""
Tests for tenant-aware Celery task routing
"""
from unittest import mock

import pytest
from celery import Task
from django.test import TestCase
from django.test import override_settings

from mate.tenants.managers import clear_current_tenant
from mate.tenants.managers import get_current_tenant
from mate.tenants.managers import set_current_tenant
from mate.tenants.models import Tenant
from mate.tenants.tasks import TenantAwareTask
from mate.tenants.tasks import cleanup_old_files
from mate.tenants.tasks import example_tenant_task
from mate.tenants.tasks import generate_report
from mate.tenants.tasks import tenant_task
from mate.users.models import User


class TestTenantAwareTask(TestCase):
    """Test tenant-aware task base class"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="testpass123",
        )

        cls.tenant_a = Tenant.objects.create(
            name="Hospital A",
            slug="hospital-a",
            subdomain="hospital-a",
            schema_name="hospital_a",
            owner=cls.user,
        )

        cls.tenant_b = Tenant.objects.create(
            name="Hospital B",
            slug="hospital-b",
            subdomain="hospital-b",
            schema_name="hospital_b",
            owner=cls.user,
        )

    def setUp(self):
        # Clear any existing tenant context
        clear_current_tenant()

    def tearDown(self):
        # Clean up tenant context
        clear_current_tenant()

    def test_task_decorator_creates_tenant_aware_task(self):
        """Test that tenant_task decorator creates TenantAwareTask instances"""

        @tenant_task(name="test_task")
        def sample_task():
            return "done"

        assert isinstance(sample_task, TenantAwareTask)
        assert sample_task.name == "test_task"

    def test_task_includes_tenant_id_in_kwargs(self):
        """Test that tenant ID is automatically added to task kwargs"""
        set_current_tenant(self.tenant_a)

        with mock.patch("mate.tenants.tasks.TenantAwareTask.run") as mock_run:
            mock_run.return_value = "success"

            # Create a task instance
            task = TenantAwareTask()
            task.name = "test_task"

            # Mock apply_async to capture the kwargs
            with mock.patch.object(Task, "apply_async") as mock_apply:
                task.apply_async(args=["arg1"], kwargs={"key": "value"})

                # Check that _tenant_id was added
                call_args = mock_apply.call_args
                # call_args is (positional_args, keyword_args)
                call_kwargs = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("kwargs", {})
                assert "_tenant_id" in call_kwargs
                assert call_kwargs["_tenant_id"] == str(self.tenant_a.id)

    @override_settings(USE_TENANT_QUEUE_ISOLATION=False)
    def test_local_routing_shared_queues(self):
        """Test that in local mode, tasks use shared queues"""
        set_current_tenant(self.tenant_a)

        task = TenantAwareTask()
        task.name = "test_task"

        with mock.patch.object(Task, "apply_async") as mock_apply:
            # Test default queue
            task.apply_async()
            assert "queue" not in mock_apply.call_args[1]

            # Test explicit queue remains unchanged
            task.apply_async(queue="gpu")
            assert mock_apply.call_args[1]["queue"] == "gpu"

    @override_settings(USE_TENANT_QUEUE_ISOLATION=True)
    def test_production_routing_tenant_queues(self):
        """Test that in production mode, tasks use tenant-specific queues"""
        set_current_tenant(self.tenant_a)

        task = TenantAwareTask()
        task.name = "test_task"

        with mock.patch.object(Task, "apply_async") as mock_apply:
            # Test default queue gets tenant prefix
            task.apply_async()
            assert mock_apply.call_args[1]["queue"] == "hospital-a-default"

            # Test explicit queue gets tenant prefix
            task.apply_async(queue="gpu")
            assert mock_apply.call_args[1]["queue"] == "hospital-a-gpu"

            # Test priority queue
            task.apply_async(queue="priority")
            assert mock_apply.call_args[1]["queue"] == "hospital-a-priority"

    def test_task_execution_sets_tenant_context(self):
        """Test that task execution properly sets and clears tenant context"""
        task = TenantAwareTask()
        task.name = "test_task"

        # Track tenant context during execution
        captured_tenant = None

        def run_impl(*args, **kwargs):
            nonlocal captured_tenant
            captured_tenant = get_current_tenant()
            return "success"

        task.run = run_impl

        # Execute task with tenant_id
        result = task(key="value", _tenant_id=str(self.tenant_a.id))

        # Check that tenant was set during execution
        assert captured_tenant == self.tenant_a
        assert result == "success"

        # Check that tenant context was cleared after execution
        assert get_current_tenant() is None

    def test_task_execution_without_tenant(self):
        """Test task execution without tenant context"""
        task = TenantAwareTask()
        task.name = "test_task"
        task.run = lambda *args, **kwargs: "success"

        with mock.patch("mate.tenants.tasks.logger.warning") as mock_warning:
            result = task()

            # Should log warning about missing tenant context
            mock_warning.assert_called_once()
            assert "without tenant context" in mock_warning.call_args[0][0]
            assert result == "success"

    def test_task_error_handling(self):
        """Test that errors are properly logged with tenant context"""
        task = TenantAwareTask()
        task.name = "test_task"

        def failing_task(*args, **kwargs):
            msg = "Task failed"
            raise ValueError(msg)

        task.run = failing_task

        with mock.patch("mate.tenants.tasks.logger.error") as mock_error:
            with pytest.raises(ValueError):
                task(_tenant_id=str(self.tenant_a.id))

            # Check error was logged with tenant info
            mock_error.assert_called_once()
            error_msg = mock_error.call_args[0][0]
            assert "hospital-a" in error_msg
            assert "Task failed" in error_msg


class TestTenantTaskExamples(TestCase):
    """Test the example tenant-aware tasks"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="testpass123",
        )

        cls.tenant = Tenant.objects.create(
            name="Test Hospital",
            slug="test-hospital",
            subdomain="test-hospital",
            schema_name="test_hospital",
            owner=cls.user,
        )

    def setUp(self):
        set_current_tenant(self.tenant)

    def tearDown(self):
        clear_current_tenant()

    @mock.patch("mate.tenants.tasks.create_audit_log")
    def test_example_tenant_task(self, mock_audit):
        """Test the example tenant task"""
        result = example_tenant_task(object_id="123", options={"test": True})

        assert result["status"] == "success"
        assert result["object_id"] == "123"

        # Check audit log was created
        mock_audit.assert_called_once_with(
            action="task_completed",
            model_name="ExampleModel",
            object_id="123",
            details={"options": {"test": True}},
        )

    @mock.patch("mate.tenants.tasks.create_audit_log")
    def test_generate_report_task(self, mock_audit):
        """Test the report generation task"""
        result = generate_report(
            report_type="monthly",
            date_range="2024-01",
            options={"format": "pdf"},
        )

        assert result["status"] == "success"
        assert result["report_type"] == "monthly"

        # Check audit log
        mock_audit.assert_called_once()
        audit_call = mock_audit.call_args[1]
        assert audit_call["action"] == "report_generated"
        assert audit_call["details"]["report_type"] == "monthly"

    def test_cleanup_task(self):
        """Test the cleanup task"""
        result = cleanup_old_files(days_to_keep=30)

        assert "deleted_count" in result
        assert isinstance(result["deleted_count"], int)


class TestQueueRouting(TestCase):
    """Test queue routing in different environments"""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="testpass123",
        )

        cls.tenant_a = Tenant.objects.create(
            name="Queue Test Hospital A",
            slug="queue-test-hospital-a",
            subdomain="queue-test-hospital-a",
            schema_name="queue_test_hospital_a",
            owner=cls.user,
        )

        cls.tenant_b = Tenant.objects.create(
            name="Queue Test Hospital B",
            slug="queue-test-hospital-b",
            subdomain="queue-test-hospital-b",
            schema_name="queue_test_hospital_b",
            owner=cls.user,
        )

    def tearDown(self):
        clear_current_tenant()

    @override_settings(USE_TENANT_QUEUE_ISOLATION=True)
    def test_different_tenants_use_different_queues(self):
        """Test that different tenants route to different queues"""
        task = TenantAwareTask()
        task.name = "test_task"

        with mock.patch.object(Task, "apply_async") as mock_apply:
            # Hospital A task
            set_current_tenant(self.tenant_a)
            task.apply_async(queue="gpu")
            hospital_a_queue = mock_apply.call_args[1]["queue"]

            # Hospital B task
            set_current_tenant(self.tenant_b)
            task.apply_async(queue="gpu")
            hospital_b_queue = mock_apply.call_args[1]["queue"]

            # Should use different queues
            assert hospital_a_queue == "queue-test-hospital-a-gpu"
            assert hospital_b_queue == "queue-test-hospital-b-gpu"
            assert hospital_a_queue != hospital_b_queue

    @override_settings(USE_TENANT_QUEUE_ISOLATION=False)
    def test_local_mode_shared_queues(self):
        """Test that local mode uses shared queues for all tenants"""
        task = TenantAwareTask()
        task.name = "test_task"

        with mock.patch.object(Task, "apply_async") as mock_apply:
            # Hospital A task
            set_current_tenant(self.tenant_a)
            task.apply_async(queue="gpu")
            hospital_a_queue = mock_apply.call_args[1]["queue"]

            # Hospital B task
            set_current_tenant(self.tenant_b)
            task.apply_async(queue="gpu")
            hospital_b_queue = mock_apply.call_args[1]["queue"]

            # Should use same queue
            assert hospital_a_queue == "gpu"
            assert hospital_b_queue == "gpu"
            assert hospital_a_queue == hospital_b_queue

    def test_queue_routing_without_tenant(self):
        """Test queue routing when no tenant is set"""
        clear_current_tenant()

        task = TenantAwareTask()
        task.name = "test_task"

        with mock.patch.object(Task, "apply_async") as mock_apply:
            task.apply_async(queue="gpu")

            # Should use original queue when no tenant
            assert mock_apply.call_args[1]["queue"] == "gpu"

