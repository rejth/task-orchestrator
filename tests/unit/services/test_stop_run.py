"""Tests for the stop_run operation — TDD vertical slices.

Integration-style: exercises real ScopedJob domain object + real service;
only the repo and Celery broker are mocked.
"""
from dataclasses import dataclass
from unittest.mock import MagicMock
from uuid import uuid4

from src.domain.job import ScopedJob
from src.domain.scoped_task import FailedScopedTask, StartedScopedTask, SuccessfullyFinishedScopedTask
from src.domain.task import TaskSpecification
from src.domain.task import TaskSpecificationId as T
from src.services.reconciliation_sweep_service import ReconciliationSweepService
from src.services.tasks_management_service import TasksManagementService
from tests.unit.domain.conftest import AT, make_scheduled_task, make_spec


@dataclass(frozen=True)
class FakeScope:
    _id: str

    def get_id(self) -> str:
        return self._id


def _make_job(scope_id: str, tasks: list) -> ScopedJob:
    return ScopedJob(id=uuid4(), scope=FakeScope(scope_id), tasks=tasks)


def _make_started_task(spec: TaskSpecification) -> StartedScopedTask:
    return make_scheduled_task(spec).start(message="started", at=AT)


def _make_service(repo, broker=None, **kwargs) -> TasksManagementService:
    return TasksManagementService(jobs_repo=repo, broker=broker or MagicMock(), **kwargs)


# ── RED slice 1: stop Job, all non-terminal Tasks transition to aborted ──────

def test_stop_run_aborts_pending_task():
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).stop_run("scope-1")

    updated_job = repo.update.call_args.kwargs["job"]
    (aborted,) = updated_job.get_tasks()
    assert isinstance(aborted, FailedScopedTask)
    assert aborted.latest_launch.metadata.is_aborted is True


def test_stop_run_aborts_in_progress_task():
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = _make_started_task(spec)
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).stop_run("scope-1")

    updated_job = repo.update.call_args.kwargs["job"]
    (aborted,) = updated_job.get_tasks()
    assert isinstance(aborted, FailedScopedTask)
    assert aborted.latest_launch.metadata.is_aborted is True


def test_stop_run_aborts_all_non_terminal_tasks():
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    spec_c = make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_SOMATIC_MUTATIONS])
    job = _make_job("scope-1", [
        _make_started_task(spec_a),
        make_scheduled_task(spec_b),
        make_scheduled_task(spec_c),
    ])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).stop_run("scope-1")

    updated_job = repo.update.call_args.kwargs["job"]
    for task in updated_job.get_tasks():
        assert isinstance(task, FailedScopedTask)
        assert task.latest_launch.metadata.is_aborted is True


def test_stop_run_leaves_terminal_tasks_unchanged():
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    finished_a = _make_started_task(spec_a).finish(message="done", at=AT)
    scheduled_b = make_scheduled_task(spec_b)
    job = _make_job("scope-1", [finished_a, scheduled_b])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).stop_run("scope-1")

    updated_job = repo.update.call_args.kwargs["job"]
    tasks_by_spec = {t.spec_id: t for t in updated_job.get_tasks()}
    assert isinstance(tasks_by_spec[T.RELOAD_PATIENT_DATA], SuccessfullyFinishedScopedTask)
    assert isinstance(tasks_by_spec[T.RELOAD_SOMATIC_MUTATIONS], FailedScopedTask)


# ── RED slice 2: dispatch path does not enqueue aborted Tasks ────────────────

def test_after_stop_run_updated_job_has_no_dispatchable_tasks():
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    _make_service(repo).stop_run("scope-1")

    updated_job = repo.update.call_args.kwargs["job"]
    assert updated_job.dispatchable_tasks() == []


def test_after_stop_run_send_to_queue_enqueues_nothing():
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    dispatcher = MagicMock()
    svc = _make_service(repo, event_driven_dispatch=True, task_dispatcher=dispatcher)
    svc.stop_run("scope-1")

    updated_job = repo.update.call_args.kwargs["job"]
    result = MagicMock()
    result.updated_job = updated_job
    svc.send_to_queue(result, user="test@user.com")

    dispatcher.dispatch.assert_called_once()
    assert dispatcher.dispatch.call_args.kwargs["tasks"] == []


# ── RED slice 3: reconciliation sweep skips aborted Tasks ───────────────────

def test_after_stop_run_reconciliation_sweep_dispatches_nothing():
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    job = _make_job("scope-1", [task])

    stop_repo = MagicMock()
    stop_repo.find_by_scope_id_for_update.return_value = job
    _make_service(stop_repo).stop_run("scope-1")
    updated_job = stop_repo.update.call_args.kwargs["job"]

    sweep_repo = MagicMock()
    sweep_repo.list_all.return_value = [updated_job]
    dispatcher = MagicMock()
    ReconciliationSweepService(
        jobs_repo=sweep_repo, dispatcher=dispatcher, system_user="system@sweep"
    ).sweep()

    dispatcher.dispatch.assert_not_called()


# ── RED slice 4: running Launches are revoked when stop-run is called ────────

def test_stop_run_revokes_in_progress_launch():
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = _make_started_task(spec)
    launch_id = task.current_launch.id
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    broker = MagicMock()
    _make_service(repo, broker).stop_run("scope-1")

    broker.control.revoke.assert_called_once_with(str(launch_id), terminate=True)


def test_stop_run_revokes_pending_launch():
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = make_scheduled_task(spec)
    launch_id = task.current_launch.id
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    broker = MagicMock()
    _make_service(repo, broker).stop_run("scope-1")

    broker.control.revoke.assert_called_once_with(str(launch_id), terminate=True)


def test_stop_run_revokes_all_active_launches():
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    started_a = _make_started_task(spec_a)
    scheduled_b = make_scheduled_task(spec_b)
    job = _make_job("scope-1", [started_a, scheduled_b])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    broker = MagicMock()
    _make_service(repo, broker).stop_run("scope-1")

    assert broker.control.revoke.call_count == 2
    revoked_ids = {c.args[0] for c in broker.control.revoke.call_args_list}
    assert revoked_ids == {str(started_a.current_launch.id), str(scheduled_b.current_launch.id)}


def test_stop_run_no_revoke_when_all_tasks_terminal():
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = _make_started_task(spec).finish(message="done", at=AT)
    job = _make_job("scope-1", [task])

    repo = MagicMock()
    repo.find_by_scope_id_for_update.return_value = job
    broker = MagicMock()
    _make_service(repo, broker).stop_run("scope-1")

    broker.control.revoke.assert_not_called()
