"""Shared helpers for service-layer unit tests."""
from dataclasses import dataclass
from unittest.mock import MagicMock
from uuid import uuid4

from src.domain.job import ScopedJob
from src.services.tasks_management_service import TasksManagementService


@dataclass(frozen=True)
class FakeScope:
    _id: str

    def get_id(self) -> str:
        return self._id


def _make_job(scope_id: str, tasks: list) -> ScopedJob:
    return ScopedJob(id=uuid4(), scope=FakeScope(scope_id), tasks=tasks)


def _make_service(repo, broker=None, **kwargs) -> TasksManagementService:
    return TasksManagementService(jobs_repo=repo, broker=broker or MagicMock(), **kwargs)
