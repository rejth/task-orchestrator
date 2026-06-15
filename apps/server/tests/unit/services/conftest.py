"""Shared helpers for service-layer unit tests."""

from dataclasses import dataclass
from unittest.mock import create_autospec
from uuid import uuid4

from celery import Celery

from task_orchestrator.domain.job import ScopedJob
from task_orchestrator.domain.jobs_repo import JobsRepository
from task_orchestrator.domain.scoped_task import ScopedTask
from task_orchestrator.services.task_dispatcher import TaskDispatcher
from task_orchestrator.services.tasks_management_service import TasksManagementService


@dataclass(frozen=True)
class FakeScope:
    _id: str

    def get_id(self) -> str:
        return self._id


def _make_job(scope_id: str, tasks: list[ScopedTask]) -> ScopedJob[FakeScope]:
    return ScopedJob(id=uuid4(), scope=FakeScope(scope_id), tasks=tasks)


def _make_service(
    repo: JobsRepository,
    broker: Celery | None = None,
    task_dispatcher: TaskDispatcher | None = None,
) -> TasksManagementService:
    return TasksManagementService(
        jobs_repo=repo,
        broker=broker or create_autospec(Celery, instance=True),
        task_dispatcher=task_dispatcher,
    )
