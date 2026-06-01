"""ScopedJob aggregate root tests."""
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from src.domain.job import (
    InvalidChangeTaskStatusOperation,
    RequiredTaskNotFinished,
    ScopedJob,
    TaskNotFound,
)
from src.domain.scoped_task import (
    LaunchNotFound,
    NewScopedTask,
    ScopedTaskStatus,
)
from src.domain.task import TaskSpecification, TaskSpecificationId
from tests.unit.domain.conftest import AT, BY, JOB_ID, make_new_task, make_spec

LAUNCH_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
T = TaskSpecificationId


@dataclass(frozen=True)
class MockScope:
    id: str = "scope-1"

    def get_id(self) -> str:
        return self.id


# Linear pipeline:
# RELOAD_PATIENT_DATA → RELOAD_MATCHED_TREATMENTS → EXPORT_TREATMENTS → PUSH_MATCHED_TREATMENTS
# Plus a parallel branch off RELOAD_PATIENT_DATA:
# RELOAD_PATIENT_DATA → RELOAD_SOMATIC_MUTATIONS (independent of treatment chain)

def _spec(id: TaskSpecificationId, depends_on: list[TaskSpecificationId] | None = None) -> TaskSpecification:
    return TaskSpecification(id=id, label=id.value, description="", depends_on=depends_on or [])


def make_fresh_job() -> ScopedJob[MockScope]:
    return ScopedJob[MockScope](
        id=JOB_ID,
        scope=MockScope(),
        tasks=[
            NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=_spec(T.RELOAD_PATIENT_DATA)),
            NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=_spec(T.RELOAD_SOMATIC_MUTATIONS, [T.RELOAD_PATIENT_DATA])),
            NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=_spec(T.RELOAD_MATCHED_TREATMENTS, [T.RELOAD_PATIENT_DATA, T.RELOAD_SOMATIC_MUTATIONS])),
            NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=_spec(T.EXPORT_TREATMENTS, [T.RELOAD_MATCHED_TREATMENTS])),
            NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=_spec(T.PUSH_MATCHED_TREATMENTS, [T.EXPORT_TREATMENTS])),
        ],
    )


def test_schedule_from_root_and_run_all():
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = result.updated_job
    for task in result.tasks_sequence:
        updated_job, started = updated_job.start(task.spec_id, task.current_launch.id, "start", AT)
        updated_job, _ = updated_job.success(task.spec_id, started.current_launch.id, "done", AT)
    for task in updated_job.get_tasks():
        assert task.status == ScopedTaskStatus.SUCCESS


def test_schedule_from_middle_reschedules_downstream():
    job = make_fresh_job()
    # Complete the full pipeline
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    job = result.updated_job
    for t in result.tasks_sequence:
        job, started = job.start(t.spec_id, t.current_launch.id, "s", AT)
        job, _ = job.success(t.spec_id, started.current_launch.id, "d", AT)
    # Re-schedule from middle
    result2 = job.schedule(task_id=T.RELOAD_MATCHED_TREATMENTS, launch_id_generator=uuid4, message="redo", at=AT, by=BY)
    scheduled_ids = {t.spec_id for t in result2.tasks_sequence}
    assert T.RELOAD_MATCHED_TREATMENTS in scheduled_ids
    assert T.EXPORT_TREATMENTS in scheduled_ids
    assert T.PUSH_MATCHED_TREATMENTS in scheduled_ids


def test_fail_task_cascades_downstream():
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = result.updated_job
    root = result.tasks_sequence[0]
    updated_job, started = updated_job.start(root.spec_id, root.current_launch.id, "s", AT)
    updated_job = updated_job.fail(
        task_id=root.spec_id, launch_id=started.current_launch.id, message="err", at=AT, is_aborted=False
    )
    for task in updated_job.get_tasks():
        assert task.status in (ScopedTaskStatus.FAILED, ScopedTaskStatus.NEW)


def test_start_raises_when_predecessor_not_finished():
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = result.updated_job
    treatment_task = next(t for t in result.tasks_sequence if t.spec_id == T.RELOAD_MATCHED_TREATMENTS)
    with pytest.raises(RequiredTaskNotFinished):
        updated_job.start(T.RELOAD_MATCHED_TREATMENTS, treatment_task.current_launch.id, "s", AT)


def test_fail_new_task_raises():
    job = make_fresh_job()
    with pytest.raises(InvalidChangeTaskStatusOperation):
        job.fail(task_id=T.RELOAD_PATIENT_DATA, launch_id=LAUNCH_ID, message="x", at=AT, is_aborted=False)


def test_task_not_found_raises():
    single: ScopedJob[MockScope] = ScopedJob(
        id=JOB_ID, scope=MockScope(),
        tasks=[NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=_spec(T.RELOAD_PATIENT_DATA))],
    )
    with pytest.raises(TaskNotFound):
        single.schedule(task_id=T.RELOAD_SOMATIC_MUTATIONS, launch_id_generator=uuid4, message="x", at=AT, by=BY)


def test_schedule_already_scheduled_task_raises():
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    with pytest.raises(InvalidChangeTaskStatusOperation):
        result.updated_job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="again", at=AT, by=BY)


def test_fail_with_wrong_launch_id_raises():
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = result.updated_job
    root = result.tasks_sequence[0]
    updated_job, started = updated_job.start(root.spec_id, root.current_launch.id, "s", AT)
    with pytest.raises(LaunchNotFound):
        updated_job.fail(task_id=root.spec_id, launch_id=uuid4(), message="err", at=AT, is_aborted=False)


# ── dispatchable_tasks ────────────────────────────────────────────────────────

def _succeed(job: ScopedJob, spec_id: TaskSpecificationId) -> ScopedJob:
    task = next(t for t in job.dispatchable_tasks() if t.spec_id == spec_id)
    job, started = job.start(spec_id, task.current_launch.id, "s", AT)
    job, _ = job.success(spec_id, started.current_launch.id, "d", AT)
    return job


def _skip(job: ScopedJob, spec_id: TaskSpecificationId) -> ScopedJob:
    task = next(t for t in job.get_tasks() if t.spec_id == spec_id)
    from src.domain.scoped_task import ScheduledScopedTask as _Sched
    assert isinstance(task, _Sched)
    job, started = job.start(spec_id, task.current_launch.id, "s", AT)
    job, _ = job.skip(spec_id, started.current_launch.id, "s", AT)
    return job


def test_dispatchable_tasks_linear_job_returns_only_root():
    job = make_fresh_job()
    scheduled = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = scheduled.updated_job

    dispatchable = updated_job.dispatchable_tasks()

    assert len(dispatchable) == 1
    assert dispatchable[0].spec_id == T.RELOAD_PATIENT_DATA


def test_dispatchable_tasks_fan_in_requires_all_predecessors():
    job = make_fresh_job()
    job = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY).updated_job

    # succeed root — only RELOAD_SOMATIC_MUTATIONS should be dispatchable, not fan-in yet
    job = _succeed(job, T.RELOAD_PATIENT_DATA)
    ids = {t.spec_id for t in job.dispatchable_tasks()}
    assert T.RELOAD_SOMATIC_MUTATIONS in ids
    assert T.RELOAD_MATCHED_TREATMENTS not in ids

    # succeed second predecessor — now fan-in becomes dispatchable
    job = _succeed(job, T.RELOAD_SOMATIC_MUTATIONS)
    ids = {t.spec_id for t in job.dispatchable_tasks()}
    assert T.RELOAD_MATCHED_TREATMENTS in ids


def test_dispatchable_tasks_skipped_predecessor_unblocks():
    job = make_fresh_job()
    job = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY).updated_job

    job = _succeed(job, T.RELOAD_PATIENT_DATA)
    job = _skip(job, T.RELOAD_SOMATIC_MUTATIONS)

    ids = {t.spec_id for t in job.dispatchable_tasks()}
    assert T.RELOAD_MATCHED_TREATMENTS in ids


def test_dispatchable_tasks_failed_predecessor_blocks():
    # Build job directly: RELOAD_PATIENT_DATA=FAILED, RELOAD_SOMATIC_MUTATIONS=PENDING
    spec_root = make_spec(T.RELOAD_PATIENT_DATA)
    spec_child = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])

    failed_root = make_new_task(spec_root).schedule(uuid4(), "s", AT, BY).start("s", AT).fail("err", AT, False)
    pending_child = make_new_task(spec_child).schedule(uuid4(), "s", AT, BY)

    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[failed_root, pending_child])

    assert job.dispatchable_tasks() == []


def test_dispatchable_tasks_new_task_never_dispatchable():
    # RELOAD_PATIENT_DATA=SUCCESS (satisfied), RELOAD_SOMATIC_MUTATIONS=NEW (never scheduled)
    spec_root = make_spec(T.RELOAD_PATIENT_DATA)
    spec_child = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])

    success_root = make_new_task(spec_root).schedule(uuid4(), "s", AT, BY).start("s", AT).finish("d", AT)
    new_child = make_new_task(spec_child)

    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[success_root, new_child])

    assert job.dispatchable_tasks() == []


def test_dispatchable_tasks_parallel_independent_children_all_returned():
    # Diamond: root → [child_a, child_b] → sink
    # After root succeeds, both children have satisfied preds → both dispatchable
    spec_root = make_spec(T.RELOAD_PATIENT_DATA)
    spec_a = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    spec_b = make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA])

    success_root = make_new_task(spec_root).schedule(uuid4(), "s", AT, BY).start("s", AT).finish("d", AT)
    pending_a = make_new_task(spec_a).schedule(uuid4(), "s", AT, BY)
    pending_b = make_new_task(spec_b).schedule(uuid4(), "s", AT, BY)

    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[success_root, pending_a, pending_b])

    ids = {t.spec_id for t in job.dispatchable_tasks()}
    assert ids == {T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_MATCHED_TREATMENTS}
