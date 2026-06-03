"""Shared fixtures and helpers for domain unit tests."""

import datetime
from uuid import UUID

from src.domain.launch import ScheduledLaunch, ScheduleMetadata
from src.domain.scoped_task import NewScopedTask, ScheduledScopedTask
from src.domain.task import TaskSpecification, TaskSpecificationId

AT = datetime.datetime(2024, 1, 15, 12, 0, 0)
BY = "tester@example.com"
JOB_ID = UUID("11111111-1111-1111-1111-111111111111")


def make_spec(
    id: TaskSpecificationId,
    label: str = "",
    depends_on: list[TaskSpecificationId] | None = None,
) -> TaskSpecification:
    return TaskSpecification(id=id, label=label or id.value, description="", depends_on=depends_on or [])


def make_new_task(spec: TaskSpecification) -> NewScopedTask:
    from uuid import uuid4

    return NewScopedTask(id=uuid4(), job_id=JOB_ID, specification=spec)


def make_scheduled_task(spec: TaskSpecification, launch_id: UUID | None = None) -> ScheduledScopedTask:
    from uuid import uuid4

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
