from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from task_orchestrator.domain.scoped_task import ScopedTaskStatus


class LaunchSchema(BaseModel):
    id: UUID
    status: str
    scheduled_at: datetime
    scheduled_by: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    is_aborted: Optional[bool] = None
    skipped_at: Optional[datetime] = None


class TaskSchema(BaseModel):
    id: UUID
    spec_id: str
    label: str
    description: str
    depends_on: list[str]
    status: ScopedTaskStatus
    current_launch: Optional[LaunchSchema] = None
    latest_launch: Optional[LaunchSchema] = None


class TaskListResponse(BaseModel):
    tasks: list[TaskSchema]


class ScheduleResponse(BaseModel):
    tasks: list[TaskSchema]


class ScopeResponse(BaseModel):
    scope_id: UUID
