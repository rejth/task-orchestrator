"""Demo task handler — always succeeds after a short sleep. Replace with real logic."""

import time

from task_orchestrator.domain.journal import Log
from task_orchestrator.handlers.interface import TaskHandleStatus


class DemoHandler:
    def run(self, scope_id: str) -> tuple[TaskHandleStatus, list[Log]]:
        time.sleep(0.5)
        return TaskHandleStatus.SUCCESS, []
