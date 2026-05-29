from typing import Optional, Protocol
from uuid import UUID

from src.domain.job import ScopedJobInterface
from src.domain.scoped_task import ScopedTask
from src.domain.task import TaskSpecification


class JobsRepository(Protocol):
    def create_job(self, scope_id: str, task_specs: list[TaskSpecification]) -> None: ...

    def update(self, job: ScopedJobInterface) -> None: ...

    def update_task(self, task: ScopedTask) -> None: ...

    def find_by_scope_id(self, scope_id: str) -> Optional[ScopedJobInterface]: ...

    def find_by_scope_id_for_update(self, scope_id: str) -> Optional[ScopedJobInterface]: ...

    def delete(self, job_id: UUID) -> None: ...
