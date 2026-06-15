"""Verify chain-level expiry wiring is removed and per-task expiry is unaffected."""

import inspect
from unittest.mock import MagicMock, patch

from task_orchestrator.api.config import Settings
from task_orchestrator.services.task_dispatcher import TaskDispatcher
from task_orchestrator.services.tasks_management_service import TasksManagementService


def test_service_has_no_chain_expires_param():
    """TasksManagementService no longer accepts chain_expires_seconds."""
    sig = inspect.signature(TasksManagementService.__init__)
    assert "chain_expires_seconds" not in sig.parameters


def test_config_has_task_expiry_seconds():
    """Settings exposes a positive TASK_EXPIRY_SECONDS."""
    s = Settings()
    assert hasattr(s, "TASK_EXPIRY_SECONDS")
    assert s.TASK_EXPIRY_SECONDS > 0


def test_config_has_no_celery_task_chain_expires():
    """Settings no longer defines CELERY_TASK_CHAIN_EXPIRES."""
    s = Settings()
    assert not hasattr(s, "CELERY_TASK_CHAIN_EXPIRES")


def test_service_default_dispatcher_uses_3600():
    """Default TaskDispatcher is constructed with expiry_seconds=3600."""
    broker = MagicMock()
    jobs_repo = MagicMock()
    with patch("task_orchestrator.services.tasks_management_service.TaskDispatcher") as MockDispatcher:
        MockDispatcher.return_value = MagicMock()
        TasksManagementService(jobs_repo=jobs_repo, broker=broker)
    MockDispatcher.assert_called_once_with(broker=broker, expiry_seconds=3600)


def test_service_accepts_injected_dispatcher():
    """TasksManagementService uses an injected TaskDispatcher when provided."""
    broker = MagicMock()
    jobs_repo = MagicMock()
    dispatcher = MagicMock(spec=TaskDispatcher)
    svc = TasksManagementService(jobs_repo=jobs_repo, broker=broker, task_dispatcher=dispatcher)
    assert svc._dispatcher is dispatcher


def test_per_task_expiry_unaffected_after_removal():
    """Dispatcher still stamps expires_at on each enqueued task."""
    import datetime

    broker = MagicMock()
    dispatcher = TaskDispatcher(broker=broker, expiry_seconds=600)
    task = MagicMock()
    task.spec_id.value = "RELOAD_PATIENT_DATA"
    task.current_launch.id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    now = datetime.datetime.now(datetime.timezone.utc)
    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.return_value = MagicMock()
        dispatcher.dispatch(tasks=[task], scope_id="scope-1", user="user@example.com")

    MockSig.return_value.apply_async.assert_called_once()
    kwargs = MockSig.call_args[1]
    expires_at_str = kwargs["args"][4]
    expires_at = datetime.datetime.fromisoformat(expires_at_str)
    assert expires_at > now
    assert expires_at < now + datetime.timedelta(seconds=700)
