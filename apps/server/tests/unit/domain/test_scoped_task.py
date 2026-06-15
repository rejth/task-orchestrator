from uuid import uuid4

import pytest

from task_orchestrator.domain.scoped_task import (
    FailedScopedTask,
    LaunchNotFound,
    NewScopedTask,
    ScheduledScopedTask,
    ScopedTaskStatus,
    SkippedScopedTask,
    StartedScopedTask,
    SuccessfullyFinishedScopedTask,
)
from task_orchestrator.domain.task import TaskSpecification, TaskSpecificationId
from tests.unit.domain.conftest import AT, BY, JOB_ID

SPEC = TaskSpecification(
    id=TaskSpecificationId.RELOAD_PATIENT_DATA, label="Reload Patient Data", description="", depends_on=[]
)


def make_new() -> NewScopedTask:
    return NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=SPEC)


def test_new_task_status():
    """A freshly created scoped task has status NEW."""
    assert make_new().status == ScopedTaskStatus.NEW


def test_new_to_scheduled():
    """Scheduling a NEW task transitions it to PENDING."""
    scheduled = make_new().schedule(uuid4(), "go", AT, BY)
    assert isinstance(scheduled, ScheduledScopedTask)
    assert scheduled.status == ScopedTaskStatus.PENDING


def test_scheduled_to_started():
    """Starting a PENDING task transitions it to IN_PROGRESS."""
    started = make_new().schedule(uuid4(), "go", AT, BY).start("start", AT)
    assert isinstance(started, StartedScopedTask)
    assert started.status == ScopedTaskStatus.IN_PROGRESS


def test_started_to_finished():
    """Finishing an IN_PROGRESS task transitions it to SUCCESS."""
    started = make_new().schedule(uuid4(), "go", AT, BY).start("start", AT)
    finished = started.finish("done", AT)
    assert isinstance(finished, SuccessfullyFinishedScopedTask)
    assert finished.status == ScopedTaskStatus.SUCCESS


def test_started_to_failed():
    """Failing an IN_PROGRESS task transitions it to FAILED."""
    started = make_new().schedule(uuid4(), "go", AT, BY).start("start", AT)
    failed = started.fail("error", AT, is_aborted=False)
    assert isinstance(failed, FailedScopedTask)
    assert failed.status == ScopedTaskStatus.FAILED


def test_started_to_skipped():
    """Skipping an IN_PROGRESS task transitions it to SKIPPED."""
    started = make_new().schedule(uuid4(), "go", AT, BY).start("start", AT)
    skipped = started.skip("skip", AT)
    assert isinstance(skipped, SkippedScopedTask)
    assert skipped.status == ScopedTaskStatus.SKIPPED


def test_finished_can_reschedule():
    """A SUCCESS task can be rescheduled and its previous launch moves to history."""
    finished = make_new().schedule(uuid4(), "go", AT, BY).start("start", AT).finish("done", AT)
    rescheduled = finished.reschedule(uuid4(), "retry", AT, BY)
    assert isinstance(rescheduled, ScheduledScopedTask)
    assert len(rescheduled.launch_history) == 1


def test_failed_can_reschedule():
    """A FAILED task can be rescheduled back to PENDING."""
    failed = make_new().schedule(uuid4(), "go", AT, BY).start("s", AT).fail("err", AT, is_aborted=False)
    assert isinstance(failed.reschedule(uuid4(), "retry", AT, BY), ScheduledScopedTask)


def test_skipped_can_reschedule():
    """A SKIPPED task can be rescheduled back to PENDING."""
    skipped = make_new().schedule(uuid4(), "go", AT, BY).start("s", AT).skip("skip", AT)
    assert isinstance(skipped.reschedule(uuid4(), "retry", AT, BY), ScheduledScopedTask)


def test_new_task_raises_launch_not_found():
    """A NEW task with no launches raises LaunchNotFound when queried by launch id."""
    with pytest.raises(LaunchNotFound):
        make_new().get_launch_by_id(uuid4())


def test_launch_history_capped_at_8():
    """Launch history retains at most eight past launches plus the latest."""
    task = make_new().schedule(uuid4(), "go", AT, BY).start("s", AT).finish("done", AT)
    for _ in range(10):
        task = task.reschedule(uuid4(), "retry", AT, BY).start("s", AT).finish("done", AT)
    assert len(task.launch_history) <= 9  # [:8] old history + 1 latest = max 9
