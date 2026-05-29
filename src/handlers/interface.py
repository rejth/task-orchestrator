from __future__ import annotations

from enum import Enum
from typing import Protocol

from src.domain.journal import Log


class TaskHandleStatus(Enum):
    SUCCESS = "SUCCESS"
    FAIL = "FAIL"
    SKIP = "SKIP"


class TaskHandlerInterface(Protocol):
    def run(self, scope_id: str) -> tuple[TaskHandleStatus, list[Log]]: ...
