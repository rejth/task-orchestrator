import datetime

from celery import Celery, chain
from celery.canvas import Signature, _chain, group

from src.domain.job import ScopedJobInterface
from src.domain.scoped_task import ScheduledScopedTask
from src.services.make_task_graph import LeafTask, ParallelTasks, SequentialTasks

TASK_NAME = "task_runner"


class CeleryChainBuilder:
    def __init__(self, job: ScopedJobInterface, user: str, chain_expires_seconds: int, broker: Celery):
        self._job = job
        self._user = user
        self._chain_expires_seconds = chain_expires_seconds
        self._broker = broker

    def make_celery_chain(self, graph: SequentialTasks) -> chain | _chain:
        return chain(*[self._make_celery_signature(task=value) for value in graph.values], app=self._broker)

    def _make_celery_group(self, task: ParallelTasks) -> group:
        items = []
        for item in task.value:
            match item:
                case LeafTask():
                    items.append(self._make_celery_signature(item))
                case SequentialTasks():
                    items.append(self.make_celery_chain(graph=item))
        return group(items)

    def _make_celery_signature(self, task: LeafTask | ParallelTasks) -> Signature | list[Signature]:
        match task:
            case LeafTask():
                return self._get_signature(task.value)
            case ParallelTasks():
                return self._make_celery_group(task=task)

    def _get_signature(self, task: ScheduledScopedTask) -> Signature:
        return Signature(
            TASK_NAME,
            args=(
                self._job.get_scope().get_id(),
                task.spec_id.value,
                str(task.current_launch.id),
                self._user,
            ),
            options={"task_id": str(task.current_launch.id)},
            immutable=True,
            expires=datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(seconds=self._chain_expires_seconds),
        )
