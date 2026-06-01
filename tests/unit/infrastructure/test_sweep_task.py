"""Tests for the reconciliation_sweep Celery periodic task wiring."""
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.celery.sweep_task import SWEEP_TASK_NAME, reconciliation_sweep


def test_sweep_task_name():
    assert reconciliation_sweep.name == SWEEP_TASK_NAME


def test_beat_schedule_contains_sweep_entry():
    from src.infrastructure.celery.app import get_celery_app
    app = get_celery_app()
    schedule = app.conf.beat_schedule
    assert "reconciliation-sweep" in schedule
    entry = schedule["reconciliation-sweep"]
    assert entry["task"] == SWEEP_TASK_NAME


def test_beat_schedule_interval_matches_settings():
    from src.api.config import get_settings
    from src.infrastructure.celery.app import get_celery_app
    settings = get_settings()
    app = get_celery_app()
    entry = app.conf.beat_schedule["reconciliation-sweep"]
    assert entry["schedule"] == settings.RECONCILIATION_SWEEP_INTERVAL_SECONDS


def test_sweep_task_calls_service_sweep():
    mock_service = MagicMock()
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session_factory = MagicMock(return_value=mock_session)

    with (
        patch("src.infrastructure.celery.sweep_task.get_session_factory", return_value=mock_session_factory),
        patch("src.infrastructure.celery.sweep_task.SQLJobsRepository"),
        patch("src.infrastructure.celery.sweep_task.TaskDispatcher"),
        patch("src.infrastructure.celery.sweep_task.ReconciliationSweepService", return_value=mock_service),
    ):
        reconciliation_sweep()

    mock_service.sweep.assert_called_once()


def test_sweep_task_commits_session():
    mock_service = MagicMock()
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session_factory = MagicMock(return_value=mock_session)

    with (
        patch("src.infrastructure.celery.sweep_task.get_session_factory", return_value=mock_session_factory),
        patch("src.infrastructure.celery.sweep_task.SQLJobsRepository"),
        patch("src.infrastructure.celery.sweep_task.TaskDispatcher"),
        patch("src.infrastructure.celery.sweep_task.ReconciliationSweepService", return_value=mock_service),
    ):
        reconciliation_sweep()

    mock_session.commit.assert_called_once()


def test_sweep_task_wires_system_user():
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session_factory = MagicMock(return_value=mock_session)
    MockService = MagicMock()

    with (
        patch("src.infrastructure.celery.sweep_task.get_session_factory", return_value=mock_session_factory),
        patch("src.infrastructure.celery.sweep_task.SQLJobsRepository"),
        patch("src.infrastructure.celery.sweep_task.TaskDispatcher"),
        patch("src.infrastructure.celery.sweep_task.ReconciliationSweepService", MockService),
    ):
        reconciliation_sweep()

    _, kwargs = MockService.call_args
    assert kwargs["system_user"] == "system@sweep"
