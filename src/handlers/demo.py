"""Demo task handler — always succeeds after a short sleep. Replace with real logic."""

import time

from src.domain.journal import Log
from src.handlers.interface import TaskHandleStatus


class DemoHandler:
    def run(self, scope_id: str) -> tuple[TaskHandleStatus, list[Log]]:
        time.sleep(0.5)
        return TaskHandleStatus.SUCCESS, []
