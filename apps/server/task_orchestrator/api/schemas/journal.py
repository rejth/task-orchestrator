from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from task_orchestrator.domain.journal import LogLevel, LogType


class JournalEntrySchema(BaseModel):
    id: UUID
    message: str
    level: LogLevel
    type: LogType
    timestamp: datetime


class JournalResponse(BaseModel):
    journal: list[JournalEntrySchema]
