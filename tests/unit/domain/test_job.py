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
from tests.unit.domain.conftest import AT, BY, JOB_ID

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
