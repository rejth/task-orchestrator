"""Unit tests for ReconciliationSweepService stalled-task selection query."""

from dataclasses import dataclass
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from task_orchestrator.domain.job import ScopedJob
from task_orchestrator.domain.launch import (
    FailedLaunch,
    FailMetadata,
    ProgressMetadata,
    ScheduledLaunch,
    ScheduleMetadata,
    SkipMetadata,
    SkippedLaunch,
    StartedLaunch,
    SuccessfullyFinishedLaunch,
    SuccessMetadata,
)
from task_orchestrator.domain.scoped_task import (
    FailedScopedTask,
    NewScopedTask,
    ScheduledScopedTask,
    SkippedScopedTask,
    StartedScopedTask,
    SuccessfullyFinishedScopedTask,
)
from task_orchestrator.domain.task import TaskSpecificationId as T
from task_orchestrator.services.reconciliation_sweep_service import ReconciliationSweepService
from tests.unit.domain.conftest import AT, BY, JOB_ID, make_spec


@dataclass(frozen=True)
class FakeScope:
    _id: str

    def get_id(self) -> str:
        return self._id


def _make_repo(jobs: list) -> MagicMock:
    repo = MagicMock()
    repo.list_all.return_value = jobs
    return repo


def _make_service(jobs: list, dispatcher=None) -> ReconciliationSweepService:
    return ReconciliationSweepService(
        jobs_repo=_make_repo(jobs),
        dispatcher=dispatcher or MagicMock(),
        system_user="system@sweep",
    )


def _make_job(scope_id: str, tasks: list) -> ScopedJob:
    return ScopedJob(id=uuid4(), scope=FakeScope(scope_id), tasks=tasks)


def _scheduled_task(spec, launch_id: UUID | None = None) -> ScheduledScopedTask:
    task_id = uuid4()
    lid = launch_id or uuid4()
    return ScheduledScopedTask(
        id=task_id,
        job_id=JOB_ID,
        specification=spec,
        launch_history=[],
        current_launch=ScheduledLaunch(
            id=lid,
            task_id=task_id,
            message="scheduled",
            journal=[],
            metadata=ScheduleMetadata(scheduled_at=AT, scheduled_by=BY),
        ),
    )


def _success_task(spec) -> SuccessfullyFinishedScopedTask:
    task_id = uuid4()
    lid = uuid4()
    return SuccessfullyFinishedScopedTask(
        id=task_id,
        job_id=JOB_ID,
        specification=spec,
        launch_history=[],
        latest_launch=SuccessfullyFinishedLaunch(
            id=lid,
            task_id=task_id,
            message="done",
            journal=[],
            metadata=SuccessMetadata(scheduled_at=AT, scheduled_by=BY, started_at=AT, finished_at=AT),
        ),
    )


def _failed_task(spec, is_aborted: bool = False) -> FailedScopedTask:
    task_id = uuid4()
    lid = uuid4()
    return FailedScopedTask(
        id=task_id,
        job_id=JOB_ID,
        specification=spec,
        launch_history=[],
        latest_launch=FailedLaunch(
            id=lid,
            task_id=task_id,
            message="failed",
            journal=[],
            metadata=FailMetadata(
                scheduled_at=AT,
                scheduled_by=BY,
                started_at=AT,
                failed_at=AT,
                is_aborted=is_aborted,
            ),
        ),
    )


def _started_task(spec) -> StartedScopedTask:
    task_id = uuid4()
    lid = uuid4()
    return StartedScopedTask(
        id=task_id,
        job_id=JOB_ID,
        specification=spec,
        launch_history=[],
        current_launch=StartedLaunch(
            id=lid,
            task_id=task_id,
            message="running",
            journal=[],
            metadata=ProgressMetadata(scheduled_at=AT, scheduled_by=BY, started_at=AT),
        ),
    )


def _skipped_task(spec) -> SkippedScopedTask:
    task_id = uuid4()
    lid = uuid4()
    return SkippedScopedTask(
        id=task_id,
        job_id=JOB_ID,
        specification=spec,
        launch_history=[],
        latest_launch=SkippedLaunch(
            id=lid,
            task_id=task_id,
            message="skipped",
            journal=[],
            metadata=SkipMetadata(scheduled_at=AT, scheduled_by=BY, started_at=AT, skipped_at=AT),
        ),
    )


def _new_task(spec) -> NewScopedTask:
    return NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=spec)


# ── selection tests ───────────────────────────────────────────────────────────


def test_pending_task_with_no_deps_is_selected():
    """A PENDING task with no dependencies is selected as stalled."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = _scheduled_task(spec)
    job = _make_job("scope-1", [task])

    result = _make_service([job]).find_stalled_tasks()

    assert len(result) == 1
    scope_id, tasks = result[0]
    assert scope_id == "scope-1"
    assert task in tasks


def test_pending_task_with_all_predecessors_satisfied_is_selected():
    """A PENDING task whose predecessors all succeeded is selected as stalled."""
    pred_spec = make_spec(T.RELOAD_PATIENT_DATA)
    dep_spec = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    predecessor = _success_task(pred_spec)
    stalled = _scheduled_task(dep_spec)
    job = _make_job("scope-1", [predecessor, stalled])

    result = _make_service([job]).find_stalled_tasks()

    assert len(result) == 1
    _, tasks = result[0]
    assert stalled in tasks


def test_failed_task_not_selected():
    """FAILED tasks are not selected as stalled."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    failed = _failed_task(spec)
    job = _make_job("scope-1", [failed])

    result = _make_service([job]).find_stalled_tasks()

    assert result == []


def test_aborted_task_not_selected():
    """Aborted FAILED tasks are not selected as stalled."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    aborted = _failed_task(spec, is_aborted=True)
    job = _make_job("scope-1", [aborted])

    result = _make_service([job]).find_stalled_tasks()

    assert result == []


def test_in_progress_task_not_selected():
    """IN_PROGRESS tasks are not selected as stalled."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    running = _started_task(spec)
    job = _make_job("scope-1", [running])

    result = _make_service([job]).find_stalled_tasks()

    assert result == []


def test_pending_task_with_unsatisfied_predecessor_not_selected():
    """PENDING tasks blocked by unfinished predecessors are not selected."""
    pred_spec = make_spec(T.RELOAD_PATIENT_DATA)
    dep_spec = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    # predecessor is still running, not finished
    predecessor = _started_task(pred_spec)
    blocked = _scheduled_task(dep_spec)
    job = _make_job("scope-1", [predecessor, blocked])

    result = _make_service([job]).find_stalled_tasks()

    assert result == []


def test_new_task_not_selected():
    """NEW tasks are not selected as stalled."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    new_task = _new_task(spec)
    job = _make_job("scope-1", [new_task])

    result = _make_service([job]).find_stalled_tasks()

    assert result == []


def test_pending_task_with_skipped_predecessor_is_selected():
    """A SKIPPED predecessor satisfies the dependency check for stalled selection."""
    pred_spec = make_spec(T.RELOAD_PATIENT_DATA)
    dep_spec = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    predecessor = _skipped_task(pred_spec)
    stalled = _scheduled_task(dep_spec)
    job = _make_job("scope-1", [predecessor, stalled])

    result = _make_service([job]).find_stalled_tasks()

    assert len(result) == 1
    _, tasks = result[0]
    assert stalled in tasks


def test_multiple_jobs_each_contribute_stalled_tasks():
    """find_stalled_tasks returns stalled tasks from every affected job."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    t1 = _scheduled_task(spec)
    t2 = _scheduled_task(spec)
    j1 = _make_job("scope-1", [t1])
    j2 = _make_job("scope-2", [t2])

    result = _make_service([j1, j2]).find_stalled_tasks()

    assert len(result) == 2
    scope_ids = {s for s, _ in result}
    assert scope_ids == {"scope-1", "scope-2"}


def test_empty_repo_returns_empty_result():
    """find_stalled_tasks returns an empty list when no jobs exist."""
    result = _make_service([]).find_stalled_tasks()
    assert result == []


# ── sweep / re-enqueue tests ──────────────────────────────────────────────────


def test_sweep_dispatches_stalled_task():
    """sweep() dispatches stalled tasks for a single job."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = _scheduled_task(spec)
    job = _make_job("scope-1", [task])
    dispatcher = MagicMock()

    _make_service([job], dispatcher=dispatcher).sweep()

    dispatcher.dispatch.assert_called_once_with([task], scope_id="scope-1", user="system@sweep")


def test_sweep_dispatches_each_job_group_separately():
    """sweep() dispatches stalled tasks once per scope."""
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    t1 = _scheduled_task(spec)
    t2 = _scheduled_task(spec)
    j1 = _make_job("scope-1", [t1])
    j2 = _make_job("scope-2", [t2])
    dispatcher = MagicMock()

    _make_service([j1, j2], dispatcher=dispatcher).sweep()

    assert dispatcher.dispatch.call_count == 2
    scope_ids = {call.kwargs["scope_id"] for call in dispatcher.dispatch.call_args_list}
    assert scope_ids == {"scope-1", "scope-2"}


def test_sweep_with_no_stalled_tasks_dispatches_nothing():
    """sweep() does nothing when no stalled tasks exist."""
    dispatcher = MagicMock()

    _make_service([], dispatcher=dispatcher).sweep()

    dispatcher.dispatch.assert_not_called()


def test_sweep_is_idempotent_same_launch_id_used_on_repeat():
    """Calling sweep twice for the same stalled task dispatches the same launch_id both times."""
    from unittest.mock import patch
    from uuid import uuid4

    launch_id = uuid4()
    spec = make_spec(T.RELOAD_PATIENT_DATA)
    task = _scheduled_task(spec, launch_id=launch_id)
    job = _make_job("scope-1", [task])

    captured_task_ids: list[str] = []

    broker = MagicMock()
    from task_orchestrator.services.task_dispatcher import TaskDispatcher

    real_dispatcher = TaskDispatcher(broker=broker, expiry_seconds=3600)
    service = _make_service([job], dispatcher=real_dispatcher)

    with patch("task_orchestrator.services.task_dispatcher.Signature") as MockSig:
        MockSig.side_effect = lambda *a, **kw: (
            captured_task_ids.append(kw["options"]["task_id"]),
            MagicMock(),
        )[1]
        service.sweep()
        service.sweep()

    assert len(captured_task_ids) == 2
    assert captured_task_ids[0] == captured_task_ids[1] == str(launch_id)
