"""Tests for task_runner expiry detection at queue processing time."""

import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from task_orchestrator.domain.job import InvalidChangeTaskStatusOperation, RequiredTaskNotFinished
from task_orchestrator.handlers.interface import TaskHandleStatus
from task_orchestrator.infrastructure.celery.runner import task_runner

SCOPE_ID = "patient-123"
TASK_ID = "RELOAD_PATIENT_DATA"
LAUNCH_ID = "11111111-1111-1111-1111-111111111111"
USER = "user@example.com"


def _make_mock_service() -> MagicMock:
    mock_service = MagicMock()
    # finish_task returns (job, successors) — configure to avoid unpack errors
    mock_service.finish_task.return_value = (MagicMock(), [])
    mock_service.skip_task.return_value = (MagicMock(), [])
    return mock_service


def _runner_patches(mock_service: MagicMock) -> tuple[Any, ...]:
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_settings = MagicMock()
    mock_settings.TASK_EXPIRY_SECONDS = 3600

    return (
        patch("task_orchestrator.api.config.get_settings", return_value=mock_settings),
        patch(
            "task_orchestrator.infrastructure.database.session.get_session_factory", return_value=mock_session_factory
        ),
        patch("task_orchestrator.infrastructure.repositories.jobs_repo.SQLJobsRepository"),
        patch("task_orchestrator.services.tasks_management_service.TasksManagementService", return_value=mock_service),
        patch(
            "task_orchestrator.infrastructure.celery.runner._run_handler", return_value=(TaskHandleStatus.SUCCESS, [])
        ),
        mock_session,
    )


def test_runner_calls_expire_task_when_expires_at_elapsed():
    mock_service = _make_mock_service()
    *patches, mock_session = _runner_patches(mock_service)
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)).isoformat()

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        task_runner.run(SCOPE_ID, TASK_ID, LAUNCH_ID, USER, past)  # type: ignore[reportFunctionMemberAccess]

    mock_service.expire_task.assert_called_once()
    mock_service.start_task.assert_not_called()


def test_runner_commits_after_expire_task():
    mock_service = _make_mock_service()
    *patches, mock_session = _runner_patches(mock_service)
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)).isoformat()

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        task_runner.run(SCOPE_ID, TASK_ID, LAUNCH_ID, USER, past)  # type: ignore[reportFunctionMemberAccess]

    mock_session.commit.assert_called_once()


def test_runner_does_not_expire_when_expires_at_is_future():
    mock_service = _make_mock_service()
    *patches, mock_session = _runner_patches(mock_service)
    future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        task_runner.run(SCOPE_ID, TASK_ID, LAUNCH_ID, USER, future)  # type: ignore[reportFunctionMemberAccess]

    mock_service.expire_task.assert_not_called()
    mock_service.start_task.assert_called_once()


def test_runner_discards_stale_expiry_when_task_already_finalized():
    """Race guard: stop_run may have already failed the task before the worker checks expiry."""
    mock_service = _make_mock_service()
    mock_service.expire_task.side_effect = InvalidChangeTaskStatusOperation(MagicMock(), "expire")
    *patches, mock_session = _runner_patches(mock_service)
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)).isoformat()

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        task_runner.run(SCOPE_ID, TASK_ID, LAUNCH_ID, USER, past)  # type: ignore[reportFunctionMemberAccess]

    mock_service.expire_task.assert_called_once()
    mock_service.start_task.assert_not_called()
    mock_session.commit.assert_not_called()


def test_runner_skips_expiry_when_predecessor_in_flight():
    """Race guard: stop_run may have aborted the predecessor while this task was queued,
    leaving it as ScheduledScopedTask — expiry is deferred and the runner exits cleanly."""
    mock_service = _make_mock_service()
    mock_service.expire_task.side_effect = RequiredTaskNotFinished(MagicMock(), MagicMock())
    *patches, mock_session = _runner_patches(mock_service)
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=1)).isoformat()

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        task_runner.run(SCOPE_ID, TASK_ID, LAUNCH_ID, USER, past)  # type: ignore[reportFunctionMemberAccess]

    mock_service.expire_task.assert_called_once()
    mock_service.start_task.assert_not_called()
    mock_session.commit.assert_not_called()


def test_runner_does_not_expire_when_no_expires_at():
    mock_service = _make_mock_service()
    *patches, mock_session = _runner_patches(mock_service)

    with patches[0], patches[1], patches[2], patches[3], patches[4]:
        task_runner.run(SCOPE_ID, TASK_ID, LAUNCH_ID, USER)  # type: ignore[reportFunctionMemberAccess]

    mock_service.expire_task.assert_not_called()
    mock_service.start_task.assert_called_once()
