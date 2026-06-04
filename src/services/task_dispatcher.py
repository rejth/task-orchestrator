import datetime

from celery import Celery
from celery.canvas import Signature

from src.domain.scoped_task import ScheduledScopedTask

TASK_NAME = "task_runner"


class TaskDispatcher:
    def __init__(self, broker: Celery, expiry_seconds: int):
        if expiry_seconds <= 0:
            raise ValueError(f"expiry_seconds must be positive, got {expiry_seconds}")
        self._broker = broker
        self._expiry_seconds = expiry_seconds

    def dispatch(self, tasks: list[ScheduledScopedTask], scope_id: str, user: str) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        for task in tasks:
            self._enqueue(task, scope_id, user, now)

    def _enqueue(self, task: ScheduledScopedTask, scope_id: str, user: str, now: datetime.datetime) -> None:
        launch_id = str(task.current_launch.id)
        expires_at = now + datetime.timedelta(seconds=self._expiry_seconds)
        Signature(
            TASK_NAME,
            args=(scope_id, task.spec_id.value, launch_id, user, expires_at.isoformat()),
            options={"task_id": launch_id},
            immutable=True,
            app=self._broker,
        ).apply_async()
