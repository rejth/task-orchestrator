"""Verify chain-level expiry wiring is removed and per-task expiry is unaffected."""

import inspect
from unittest.mock import MagicMock, patch

from src.api.config import Settings
from src.services.task_dispatcher import TaskDispatcher
from src.services.tasks_management_service import TasksManagementService


def test_service_has_no_chain_expires_param():
    sig = inspect.signature(TasksManagementService.__init__)
    assert "chain_expires_seconds" not in sig.parameters


def test_config_has_task_expiry_seconds():
    s = Settings()
    assert hasattr(s, "TASK_EXPIRY_SECONDS")
    assert s.TASK_EXPIRY_SECONDS > 0


def test_config_has_no_celery_task_chain_expires():
    s = Settings()
    assert not hasattr(s, "CELERY_TASK_CHAIN_EXPIRES")


def test_service_default_dispatcher_uses_3600():
    broker = MagicMock()
    jobs_repo = MagicMock()
    with patch("src.services.tasks_management_service.TaskDispatcher") as MockDispatcher:
        MockDispatcher.return_value = MagicMock()
        TasksManagementService(jobs_repo=jobs_repo, broker=broker)
    MockDispatcher.assert_called_once_with(broker=broker, expiry_seconds=3600)


def test_service_accepts_injected_dispatcher():
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
    with patch("src.services.task_dispatcher.Signature") as MockSig:
        MockSig.return_value = MagicMock()
        dispatcher.dispatch(tasks=[task], scope_id="scope-1", user="user@example.com")

    MockSig.return_value.apply_async.assert_called_once()
    kwargs = MockSig.call_args[1]
    expires_at_str = kwargs["args"][4]
    expires_at = datetime.datetime.fromisoformat(expires_at_str)
    assert expires_at > now
    assert expires_at < now + datetime.timedelta(seconds=700)
