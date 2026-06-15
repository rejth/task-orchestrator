"""ScopedJob aggregate root tests."""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from task_orchestrator.domain.job import (
    InvalidChangeTaskStatusOperation,
    RequiredTaskNotFinished,
    ScopedJob,
    ScopedJobInterface,
    TaskNotFound,
)
from task_orchestrator.domain.scoped_task import (
    LaunchNotFound,
    NewScopedTask,
    ScheduledScopedTask,
    ScopedTaskStatus,
)
from task_orchestrator.domain.task import TaskSpecificationId
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


def make_fresh_job() -> ScopedJob[MockScope]:
    return ScopedJob[MockScope](
        id=JOB_ID,
        scope=MockScope(),
        tasks=[
            NewScopedTask(
                id=uuid4(),
                job_id=JOB_ID,
                specification=make_spec(T.RELOAD_PATIENT_DATA),
            ),
            NewScopedTask(
                id=uuid4(),
                job_id=JOB_ID,
                specification=make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA]),
            ),
            NewScopedTask(
                id=uuid4(),
                job_id=JOB_ID,
                specification=make_spec(
                    T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA, T.RELOAD_SOMATIC_MUTATIONS]
                ),
            ),
            NewScopedTask(
                id=uuid4(),
                job_id=JOB_ID,
                specification=make_spec(T.EXPORT_TREATMENTS, depends_on=[T.RELOAD_MATCHED_TREATMENTS]),
            ),
            NewScopedTask(
                id=uuid4(),
                job_id=JOB_ID,
                specification=make_spec(T.PUSH_MATCHED_TREATMENTS, depends_on=[T.EXPORT_TREATMENTS]),
            ),
        ],
    )


def test_schedule_from_root_and_run_all():
    """Scheduling from the root task runs the full pipeline to SUCCESS."""
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = result.updated_job
    for task in result.tasks_sequence:
        updated_job, started = updated_job.start(task.spec_id, task.current_launch.id, "start", AT)
        updated_job, _ = updated_job.success(task.spec_id, started.current_launch.id, "done", AT)

    for task in updated_job.get_tasks():
        assert task.status == ScopedTaskStatus.SUCCESS


def test_schedule_from_middle_reschedules_downstream():
    """Re-scheduling a completed middle task also schedules all downstream tasks."""
    job = make_fresh_job()
    # Complete the full pipeline
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    job = result.updated_job
    for task in result.tasks_sequence:
        job, started = job.start(task.spec_id, task.current_launch.id, "s", AT)
        job, _ = job.success(task.spec_id, started.current_launch.id, "d", AT)
    # Re-schedule from middle
    result2 = job.schedule(task_id=T.RELOAD_MATCHED_TREATMENTS, launch_id_generator=uuid4, message="redo", at=AT, by=BY)
    scheduled_ids = {task.spec_id for task in result2.tasks_sequence}

    assert T.RELOAD_MATCHED_TREATMENTS in scheduled_ids
    assert T.EXPORT_TREATMENTS in scheduled_ids
    assert T.PUSH_MATCHED_TREATMENTS in scheduled_ids


def test_fail_task_cascades_downstream():
    """Failing a running root task marks it FAILED and leaves downstream tasks NEW."""
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
    """Starting a task before its predecessors finish raises RequiredTaskNotFinished."""
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = result.updated_job
    treatment_task = next(task for task in result.tasks_sequence if task.spec_id == T.RELOAD_MATCHED_TREATMENTS)

    with pytest.raises(RequiredTaskNotFinished):
        updated_job.start(T.RELOAD_MATCHED_TREATMENTS, treatment_task.current_launch.id, "s", AT)


def test_fail_new_task_raises():
    """Failing a NEW task (never scheduled) raises InvalidChangeTaskStatusOperation."""
    job = make_fresh_job()
    with pytest.raises(InvalidChangeTaskStatusOperation):
        job.fail(task_id=T.RELOAD_PATIENT_DATA, launch_id=LAUNCH_ID, message="x", at=AT, is_aborted=False)


def test_task_not_found_raises():
    """Scheduling a task spec that is not in the job raises TaskNotFound."""
    single: ScopedJob[MockScope] = ScopedJob(
        id=JOB_ID,
        scope=MockScope(),
        tasks=[NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=make_spec(T.RELOAD_PATIENT_DATA))],
    )
    with pytest.raises(TaskNotFound):
        single.schedule(task_id=T.RELOAD_SOMATIC_MUTATIONS, launch_id_generator=uuid4, message="x", at=AT, by=BY)


def test_schedule_already_scheduled_task_raises():
    """Re-scheduling a task that is already PENDING raises InvalidChangeTaskStatusOperation."""
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)

    with pytest.raises(InvalidChangeTaskStatusOperation):
        result.updated_job.schedule(
            task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="again", at=AT, by=BY
        )


def test_fail_with_wrong_launch_id_raises():
    """Failing a task with a launch_id that does not match the current launch raises LaunchNotFound."""
    job = make_fresh_job()
    result = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = result.updated_job
    root = result.tasks_sequence[0]
    updated_job, started = updated_job.start(root.spec_id, root.current_launch.id, "s", AT)

    with pytest.raises(LaunchNotFound):
        updated_job.fail(task_id=root.spec_id, launch_id=uuid4(), message="err", at=AT, is_aborted=False)


# ── dispatchable_tasks ────────────────────────────────────────────────────────


def _succeed(job: ScopedJobInterface[MockScope], spec_id: TaskSpecificationId) -> ScopedJobInterface[MockScope]:
    task = next((task for task in job.get_tasks() if task.spec_id == spec_id), None)
    assert task is not None and isinstance(task, ScheduledScopedTask), f"{spec_id} not scheduled"
    job, started = job.start(spec_id, task.current_launch.id, "s", AT)
    job, _ = job.success(spec_id, started.current_launch.id, "d", AT)
    return job


def _skip(job: ScopedJobInterface[MockScope], spec_id: TaskSpecificationId) -> ScopedJobInterface[MockScope]:
    task = next((task for task in job.get_tasks() if task.spec_id == spec_id), None)
    assert task is not None and isinstance(task, ScheduledScopedTask), f"{spec_id} not scheduled"
    job, started = job.start(spec_id, task.current_launch.id, "s", AT)
    job, _ = job.skip(spec_id, started.current_launch.id, "s", AT)
    return job


def test_dispatchable_tasks_linear_job_returns_only_root():
    """After scheduling a linear job, only the root task with no predecessors is dispatchable."""
    job = make_fresh_job()
    scheduled = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY)
    updated_job = scheduled.updated_job

    dispatchable = updated_job.dispatchable_tasks()

    assert len(dispatchable) == 1
    assert dispatchable[0].spec_id == T.RELOAD_PATIENT_DATA


def test_dispatchable_tasks_fan_in_requires_all_predecessors():
    """A fan-in task becomes dispatchable only after every predecessor has succeeded."""
    job = make_fresh_job()
    job = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY).updated_job

    # succeed root — only RELOAD_SOMATIC_MUTATIONS should be dispatchable, not fan-in yet
    job = _succeed(job, T.RELOAD_PATIENT_DATA)
    ids = {task.spec_id for task in job.dispatchable_tasks()}
    assert ids == {T.RELOAD_SOMATIC_MUTATIONS}

    # succeed second predecessor — now fan-in becomes dispatchable
    job = _succeed(job, T.RELOAD_SOMATIC_MUTATIONS)
    ids = {task.spec_id for task in job.dispatchable_tasks()}
    assert ids == {T.RELOAD_MATCHED_TREATMENTS}


def test_dispatchable_tasks_skipped_predecessor_unblocks():
    """A SKIPPED predecessor satisfies the dependency check like SUCCESS."""
    job = make_fresh_job()
    job = job.schedule(task_id=T.RELOAD_PATIENT_DATA, launch_id_generator=uuid4, message="go", at=AT, by=BY).updated_job

    job = _succeed(job, T.RELOAD_PATIENT_DATA)
    job = _skip(job, T.RELOAD_SOMATIC_MUTATIONS)

    ids = {task.spec_id for task in job.dispatchable_tasks()}
    assert T.RELOAD_MATCHED_TREATMENTS in ids


def test_dispatchable_tasks_failed_predecessor_blocks():
    """A PENDING task stays undispatchable when a predecessor is FAILED."""
    # Build job directly: RELOAD_PATIENT_DATA=FAILED, RELOAD_SOMATIC_MUTATIONS=PENDING
    spec_root = make_spec(T.RELOAD_PATIENT_DATA)
    spec_child = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])

    failed_root = make_new_task(spec_root).schedule(uuid4(), "s", AT, BY).start("s", AT).fail("err", AT, False)
    pending_child = make_new_task(spec_child).schedule(uuid4(), "s", AT, BY)

    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[failed_root, pending_child])

    assert job.dispatchable_tasks() == []


def test_dispatchable_tasks_new_task_never_dispatchable():
    """NEW tasks are never returned by dispatchable_tasks(), even when predecessors succeeded."""
    # RELOAD_PATIENT_DATA=SUCCESS (satisfied), RELOAD_SOMATIC_MUTATIONS=NEW (never scheduled)
    spec_root = make_spec(T.RELOAD_PATIENT_DATA)
    spec_child = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])

    success_root = make_new_task(spec_root).schedule(uuid4(), "s", AT, BY).start("s", AT).finish("d", AT)
    new_child = make_new_task(spec_child)

    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[success_root, new_child])

    assert job.dispatchable_tasks() == []


def test_dispatchable_tasks_parallel_independent_children_all_returned():
    """After the root succeeds, all parallel PENDING children with satisfied predecessors are dispatchable."""
    # Diamond: root → [child_a, child_b] → sink
    # After root succeeds, both children have satisfied predecessors → both dispatchable
    spec_root = make_spec(T.RELOAD_PATIENT_DATA)
    spec_a = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    spec_b = make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA])

    success_root = make_new_task(spec_root).schedule(uuid4(), "s", AT, BY).start("s", AT).finish("d", AT)
    pending_a = make_new_task(spec_a).schedule(uuid4(), "s", AT, BY)
    pending_b = make_new_task(spec_b).schedule(uuid4(), "s", AT, BY)

    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[success_root, pending_a, pending_b])

    ids = {task.spec_id for task in job.dispatchable_tasks()}
    assert ids == {T.RELOAD_SOMATIC_MUTATIONS, T.RELOAD_MATCHED_TREATMENTS}


def test_dispatchable_tasks_started_predecessor_blocks():
    """A PENDING task stays undispatchable while a predecessor is still IN_PROGRESS."""
    spec_root = make_spec(T.RELOAD_PATIENT_DATA)
    spec_child = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])

    started_root = make_new_task(spec_root).schedule(uuid4(), "s", AT, BY).start("s", AT)
    pending_child = make_new_task(spec_child).schedule(uuid4(), "s", AT, BY)

    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[started_root, pending_child])

    assert job.dispatchable_tasks() == []


def test_dispatchable_tasks_empty_job_returns_empty():
    """A job with no tasks returns an empty dispatchable list."""
    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[])

    assert job.dispatchable_tasks() == []


def test_dispatchable_tasks_missing_predecessor_treated_as_unsatisfied():
    """A missing predecessor in the job is treated as unsatisfied and blocks dispatch."""
    # Child references a predecessor ID not present in self.tasks — must not raise, must block.
    spec_child = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    pending_child = make_new_task(spec_child).schedule(uuid4(), "s", AT, BY)

    job: ScopedJob = ScopedJob(id=JOB_ID, scope=MockScope(), tasks=[pending_child])

    assert job.dispatchable_tasks() == []
