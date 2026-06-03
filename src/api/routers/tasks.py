import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from src.api.deps import get_db, get_service, get_tasks_repo, verify_api_key
from src.api.schemas.journal import JournalEntrySchema, JournalResponse
from src.api.schemas.tasks import ScheduleResponse, TaskListResponse, TaskSchema
from src.domain.job import TaskNotFound
from src.domain.launch import (
    FailedLaunch,
    SkippedLaunch,
    StartedLaunch,
    SuccessfullyFinishedLaunch,
    TaskLaunch,
)
from src.domain.scoped_task import (
    FailedScopedTask,
    LaunchNotFound,
    ScheduledScopedTask,
    ScopedTask,
    SkippedScopedTask,
    StartedScopedTask,
    SuccessfullyFinishedScopedTask,
)
from src.domain.task import TaskSpecificationId
from src.infrastructure.repositories.tasks_repo import FsTaskSpecificationsRepo
from src.services.tasks_management_service import JobNotFound, TasksManagementService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scopes", tags=["tasks"])


def _launch_to_dict(launch: TaskLaunch | None) -> Optional[dict[str, Any]]:
    if launch is None:
        return None
    dict_launch: dict[str, Any] = {
        "id": str(launch.id),
        "status": launch.status.value,
        "scheduled_at": launch.scheduled_at.isoformat(),
        "scheduled_by": launch.scheduled_by,
    }
    match launch:
        case StartedLaunch():
            dict_launch["started_at"] = launch.metadata.started_at.isoformat()
        case SuccessfullyFinishedLaunch():
            dict_launch["started_at"] = launch.metadata.started_at.isoformat()
            dict_launch["finished_at"] = launch.metadata.finished_at.isoformat()
        case FailedLaunch():
            dict_launch["started_at"] = launch.metadata.started_at.isoformat()
            dict_launch["failed_at"] = launch.metadata.failed_at.isoformat()
            dict_launch["is_aborted"] = launch.metadata.is_aborted
        case SkippedLaunch():
            dict_launch["started_at"] = launch.metadata.started_at.isoformat()
            dict_launch["skipped_at"] = launch.metadata.skipped_at.isoformat()
    return dict_launch


def _task_to_schema(task: ScopedTask) -> TaskSchema:
    current_launch = None
    latest_launch = None
    match task:
        case ScheduledScopedTask() | StartedScopedTask():
            current_launch = _launch_to_dict(task.current_launch)
        case SuccessfullyFinishedScopedTask() | FailedScopedTask() | SkippedScopedTask():
            latest_launch = _launch_to_dict(task.latest_launch)

    return TaskSchema(
        id=task.id,
        spec_id=task.spec_id.value,
        label=task.specification.label,
        description=task.specification.description,
        depends_on=[task_id.value for task_id in task.specification.depends_on],
        status=task.status,
        current_launch=current_launch,
        latest_launch=latest_launch,
    )


@router.post("/{scope_id}", status_code=201)
def init_scope(
    scope_id: UUID,
    service: TasksManagementService = Depends(get_service),
    tasks_repo: FsTaskSpecificationsRepo = Depends(get_tasks_repo),
) -> dict[str, str]:
    """Create a new job for a scope. Idempotent — returns 409 if it already exists."""
    scope_str = str(scope_id)
    existing = service._jobs_repo.find_by_scope_id(scope_id=scope_str)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Scope already exists")
    specs = tasks_repo.all()
    service.create_job(scope_id=scope_str, task_specs=specs)
    return {"scope_id": scope_str}


@router.get("/{scope_id}/tasks", response_model=TaskListResponse)
def get_tasks(
    scope_id: UUID,
    service: TasksManagementService = Depends(get_service),
) -> TaskListResponse:
    try:
        tasks = service.get_tasks(scope_id=str(scope_id))
        return TaskListResponse(tasks=[_task_to_schema(t) for t in tasks])
    except JobNotFound as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.post("/{scope_id}/tasks/{task_id}/schedule", status_code=202, response_model=ScheduleResponse)
def schedule_task(
    scope_id: UUID,
    task_id: str,
    db: Session = Depends(get_db),
    service: TasksManagementService = Depends(get_service),
    api_key: str = Depends(verify_api_key),
) -> ScheduleResponse:
    try:
        spec_id = TaskSpecificationId(task_id)
        result = service.schedule_task(scope_id=str(scope_id), task_id=spec_id, user=api_key)
        db.commit()
        try:
            service.send_to_queue(result=result, user=api_key)
        except Exception as dispatch_err:
            logger.error(
                "Dispatch failed after commit for scope %s — reconciliation sweep will retry: %s",
                scope_id,
                dispatch_err,
                exc_info=dispatch_err,
            )
        return ScheduleResponse(tasks=[_task_to_schema(t) for t in result.tasks_sequence])
    except (JobNotFound, TaskNotFound) as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))


@router.delete("/{scope_id}/run", status_code=204)
def stop_run(
    scope_id: UUID,
    service: TasksManagementService = Depends(get_service),
    api_key: str = Depends(verify_api_key),
) -> Response:
    try:
        service.stop_run(scope_id=str(scope_id))
        return Response(status_code=204)
    except JobNotFound as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.delete("/{scope_id}/tasks/{task_id}/launches/{launch_id}", status_code=204)
def abort_task(
    scope_id: UUID,
    task_id: str,
    launch_id: str,
    service: TasksManagementService = Depends(get_service),
) -> Response:
    try:
        spec_id = TaskSpecificationId(task_id)
        launch_uuid = UUID(launch_id)
        service.abort_task(scope_id=str(scope_id), task_id=spec_id, launch_id=launch_uuid, is_aborted=True)
        return Response(status_code=204)
    except (JobNotFound, TaskNotFound, LaunchNotFound) as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))


@router.get("/{scope_id}/tasks/{task_id}/launches/{launch_id}/journal", response_model=JournalResponse)
def get_journal(
    scope_id: UUID,
    task_id: str,
    launch_id: str,
    service: TasksManagementService = Depends(get_service),
) -> JournalResponse:
    try:
        spec_id = TaskSpecificationId(task_id)
        launch_uuid = UUID(launch_id)
        entries = service.get_journal(scope_id=str(scope_id), task_id=spec_id, launch_id=launch_uuid)
        journal = [
            JournalEntrySchema(
                id=e.id,
                message=e.log.message,
                level=e.log.level,
                type=e.log.type,
                timestamp=e.log.timestamp,
            )
            for e in entries
        ]
        return JournalResponse(journal=journal)
    except (JobNotFound, TaskNotFound, LaunchNotFound) as err:
        raise HTTPException(status_code=404, detail=str(err))
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err))
