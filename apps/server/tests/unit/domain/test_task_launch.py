import datetime
from uuid import uuid4

from task_orchestrator.domain.launch import (
    FailedLaunch,
    ScheduledLaunch,
    ScheduleMetadata,
    SkippedLaunch,
    StartedLaunch,
    SuccessfullyFinishedLaunch,
    TaskLaunchStatus,
)

AT = datetime.datetime(2024, 1, 15, 12, 0)
BY = "tester@example.com"


def make_scheduled() -> ScheduledLaunch:
    return ScheduledLaunch(
        id=uuid4(),
        task_id=uuid4(),
        message="scheduled",
        journal=[],
        metadata=ScheduleMetadata(scheduled_at=AT, scheduled_by=BY),
    )


def test_scheduled_launch_status():
    assert make_scheduled().status == TaskLaunchStatus.PENDING


def test_scheduled_to_started():
    started = make_scheduled().start(message="started", at=AT)
    assert isinstance(started, StartedLaunch)
    assert started.status == TaskLaunchStatus.IN_PROGRESS
    assert started.metadata.started_at == AT


def test_started_to_success():
    finished = make_scheduled().start("ok", AT).success("done", AT)
    assert isinstance(finished, SuccessfullyFinishedLaunch)
    assert finished.status == TaskLaunchStatus.FINISHED
    assert finished.metadata.finished_at == AT


def test_started_to_failed():
    failed = make_scheduled().start("ok", AT).fail("error", AT, is_aborted=False)
    assert isinstance(failed, FailedLaunch)
    assert failed.status == TaskLaunchStatus.FAILED
    assert failed.metadata.is_aborted is False


def test_started_to_aborted():
    aborted = make_scheduled().start("ok", AT).fail("aborted", AT, is_aborted=True)
    assert isinstance(aborted, FailedLaunch)
    assert aborted.metadata.is_aborted is True


def test_started_to_skipped():
    skipped = make_scheduled().start("ok", AT).skip("skip", AT)
    assert isinstance(skipped, SkippedLaunch)
    assert skipped.status == TaskLaunchStatus.SKIPPED


def test_scheduled_direct_fail():
    failed = make_scheduled().fail("immediate fail", AT, is_aborted=False)
    assert isinstance(failed, FailedLaunch)
    assert failed.status == TaskLaunchStatus.FAILED
