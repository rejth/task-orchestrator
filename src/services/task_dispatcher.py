import datetime

from celery import Celery
from celery.canvas import Signature

from src.domain.scoped_task import ScheduledScopedTask
from src.services.make_celery_chain import TASK_NAME


class TaskDispatcher:
    def __init__(self, broker: Celery, expiry_seconds: int):
        self._broker = broker
        self._expiry_seconds = expiry_seconds

    def dispatch(self, tasks: list[ScheduledScopedTask], scope_id: str, user: str) -> None:
        for task in tasks:
            self._enqueue(task, scope_id, user)

    def _enqueue(self, task: ScheduledScopedTask, scope_id: str, user: str) -> None:
        launch_id = str(task.current_launch.id)
        Signature(
            TASK_NAME,
            args=(scope_id, task.spec_id.value, launch_id, user),
            options={"task_id": launch_id},
            immutable=True,
            expires=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=self._expiry_seconds),
            app=self._broker,
        ).apply_async()
