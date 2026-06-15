"""Tests for per-task expiry — TDD vertical slices.

Integration-style: exercises real ScopedJob domain object + real service;
only the repo and Celery broker are mocked.
"""

from unittest.mock import MagicMock

from task_orchestrator.domain.scoped_task import FailedScopedTask
from task_orchestrator.domain.task import TaskSpecificationId as T
from tests.unit.domain.conftest import make_scheduled_task, make_spec
from tests.unit.services.conftest import _make_job, _make_service

# ── RED slice 2: expired Task detected at queue processing time ──────────────


def test_expire_task_transitions_pending_to_failed():
    """expire_task transitions a PENDING task to FAILED."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    launch_id = task.current_launch.id
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).expire_task(scope_id="scope-1", task_id=T.RELOAD_PATIENT_DATA, launch_id=launch_id)

    updated_job = repo.update.call_args.kwargs["job"]
    (expired_task,) = updated_job.get_tasks()
    assert isinstance(expired_task, FailedScopedTask)


# ── RED slice 3: expired Task finalized as revoked then failed ───────────────


def test_expire_task_sets_aborted_flag():
    """expire_task marks the launch as aborted."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    launch_id = task.current_launch.id
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).expire_task(scope_id="scope-1", task_id=T.RELOAD_PATIENT_DATA, launch_id=launch_id)

    updated_job = repo.update.call_args.kwargs["job"]
    (expired_task,) = updated_job.get_tasks()
    assert expired_task.latest_launch.metadata.is_aborted is True


def test_expire_task_message_indicates_expiry():
    """expire_task sets a launch message mentioning expiry."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    launch_id = task.current_launch.id
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).expire_task(scope_id="scope-1", task_id=T.RELOAD_PATIENT_DATA, launch_id=launch_id)

    updated_job = repo.update.call_args.kwargs["job"]
    (expired_task,) = updated_job.get_tasks()
    assert "expired" in expired_task.latest_launch.message.lower()


def test_expired_task_no_longer_dispatchable():
    """An expired task is no longer returned by dispatchable_tasks()."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    launch_id = task.current_launch.id
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).expire_task(scope_id="scope-1", task_id=T.RELOAD_PATIENT_DATA, launch_id=launch_id)

    updated_job = repo.update.call_args.kwargs["job"]
    assert updated_job.dispatchable_tasks() == []
