"""Tests for the reconciliation_sweep Celery periodic task wiring."""

from unittest.mock import MagicMock, patch

import pytest

from task_orchestrator.infrastructure.celery.sweep_task import SWEEP_TASK_NAME, reconciliation_sweep


@pytest.fixture()
def sweep_mocks():
    mock_service = MagicMock()
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session_factory = MagicMock(return_value=mock_session)
    MockService = MagicMock(return_value=mock_service)
    mock_settings = MagicMock()
    mock_settings.TASK_EXPIRY_SECONDS = 3600

    with (
        patch("task_orchestrator.infrastructure.celery.sweep_task.get_settings", return_value=mock_settings),
        patch("task_orchestrator.infrastructure.celery.sweep_task.get_session_factory", return_value=mock_session_factory),
        patch("task_orchestrator.infrastructure.celery.sweep_task.SQLJobsRepository"),
        patch("task_orchestrator.infrastructure.celery.sweep_task.TaskDispatcher"),
        patch("task_orchestrator.infrastructure.celery.sweep_task.ReconciliationSweepService", MockService),
    ):
        yield {"service": mock_service, "session": mock_session, "MockService": MockService}


def test_sweep_task_name():
    assert reconciliation_sweep.name == SWEEP_TASK_NAME  # type: ignore[attr-defined]


def test_beat_schedule_contains_sweep_entry():
    from task_orchestrator.infrastructure.celery.app import get_celery_app

    app = get_celery_app()
    schedule = app.conf.beat_schedule
    assert "reconciliation-sweep" in schedule
    entry = schedule["reconciliation-sweep"]
    assert entry["task"] == SWEEP_TASK_NAME


def test_beat_schedule_interval_matches_settings():
    from task_orchestrator.api.config import get_settings
    from task_orchestrator.infrastructure.celery.app import get_celery_app

    settings = get_settings()
    app = get_celery_app()
    entry = app.conf.beat_schedule["reconciliation-sweep"]
    assert entry["schedule"] == settings.RECONCILIATION_SWEEP_INTERVAL_SECONDS



def test_sweep_task_calls_service_sweep(sweep_mocks):
    reconciliation_sweep()
    sweep_mocks["service"].sweep.assert_called_once()


def test_sweep_task_does_not_commit_session(sweep_mocks):
    reconciliation_sweep()
    sweep_mocks["session"].commit.assert_not_called()


def test_sweep_task_wires_system_user(sweep_mocks):
    reconciliation_sweep()
    _, kwargs = sweep_mocks["MockService"].call_args
    assert kwargs["system_user"] == "system@sweep"


def test_sweep_task_propagates_exception_from_sweep(sweep_mocks):
    sweep_mocks["service"].sweep.side_effect = RuntimeError("broker down")
    with pytest.raises(RuntimeError, match="broker down"):
        reconciliation_sweep()
    sweep_mocks["session"].commit.assert_not_called()
