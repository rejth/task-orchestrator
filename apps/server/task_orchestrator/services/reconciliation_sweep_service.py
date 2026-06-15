from task_orchestrator.domain.jobs_repo import JobsRepository
from task_orchestrator.domain.scoped_task import ScheduledScopedTask
from task_orchestrator.services.task_dispatcher import TaskDispatcher


class ReconciliationSweepService:
    """Finds tasks stuck in PENDING in Postgres and re-enqueues them to Celery.

    Postgres is the source of truth for task state.
    When dispatch fails after a DB commit (or a message is dropped), tasks stay PENDING
    even though they are ready to run. The periodic sweep finds those tasks via
    ``dispatchable_tasks()`` and dispatches them again using the existing launch_id.

    A task counts as stalled when it is:

    - ``PENDING`` (``ScheduledScopedTask``), and
    - every predecessor is ``SUCCESS`` or ``SKIPPED``.

    Not stalled: ``NEW``, ``IN_PROGRESS``, ``FAILED``/aborted, or ``PENDING`` but blocked
    by a predecessor that has not finished yet.
    """

    def __init__(self, jobs_repo: JobsRepository, dispatcher: TaskDispatcher, system_user: str):
        self._jobs_repo = jobs_repo
        self._dispatcher = dispatcher
        self._system_user = system_user

    def find_stalled_tasks(self) -> list[tuple[str, list[ScheduledScopedTask]]]:
        """Returns (scope_id, tasks) for each job that has PENDING tasks with all predecessors satisfied."""
        result = []
        for job in self._jobs_repo.list_all():
            tasks = job.dispatchable_tasks()
            if tasks:
                result.append((job.get_scope().get_id(), tasks))
        return result

    def sweep(self) -> None:
        for scope_id, tasks in self.find_stalled_tasks():
            self._dispatcher.dispatch(tasks, scope_id=scope_id, user=self._system_user)
