from typing import Protocol

from task_orchestrator.domain.task import TaskSpecification, TaskSpecificationId


class TaskSpecificationsRepository(Protocol):
    def all(self) -> list[TaskSpecification]: ...

    def find_tasks_by_ids(self, task_ids: list[TaskSpecificationId]) -> list[TaskSpecification]: ...
