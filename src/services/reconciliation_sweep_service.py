from src.domain.jobs_repo import JobsRepository
from src.domain.scoped_task import ScheduledScopedTask


class ReconciliationSweepService:
    def __init__(self, jobs_repo: JobsRepository):
        self._jobs_repo = jobs_repo

    def find_stalled_tasks(self) -> list[tuple[str, list[ScheduledScopedTask]]]:
        """Returns (scope_id, tasks) for each job that has PENDING tasks with all predecessors satisfied."""
        result = []
        for job in self._jobs_repo.list_all():
            tasks = job.dispatchable_tasks()
            if tasks:
                result.append((job.get_scope().get_id(), tasks))
        return result
