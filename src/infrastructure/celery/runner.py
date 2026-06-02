"""Celery task that executes a single scoped task."""

import datetime
import logging
from uuid import UUID

from celery import Task as CeleryTask
from celery.exceptions import TaskError

from src.domain.job import InvalidChangeTaskStatusOperation, RequiredTaskNotFinished
from src.domain.journal import Log, LogLevel, UnclassifiedLogRecord
from src.domain.scoped_task import LaunchNotFound
from src.domain.task import TaskSpecificationId
from src.handlers.demo import DemoHandler
from src.handlers.interface import TaskHandleStatus
from src.infrastructure.celery.app import get_celery_app
from src.services.make_celery_chain import TASK_NAME

logger = logging.getLogger(__name__)

_HANDLERS: dict[TaskSpecificationId, type] = dict.fromkeys(TaskSpecificationId, DemoHandler)

celery_app = get_celery_app()


class TaskExecutionError(TaskError):
    def __init__(self, task_id: str, scope_id: str, launch_id: str):
        self._task_id = task_id
        self._scope_id = scope_id
        self._launch_id = launch_id

    def __str__(self) -> str:
        return f"Error executing task <id={self._task_id}, scope={self._scope_id}, launch={self._launch_id}>"


@celery_app.task(name=TASK_NAME, bind=True, max_retries=0)
def task_runner(
    self: CeleryTask, scope_id: str, task_id: str, launch_id: str, user: str, expires_at: str | None = None
) -> None:
    logger.info("Starting task %s launch %s for scope %s", task_id, launch_id, scope_id)
    task_spec_id = TaskSpecificationId(task_id)
    launch_uuid = UUID(launch_id)

    from src.infrastructure.database.session import get_session_factory
    from src.infrastructure.repositories.jobs_repo import SQLJobsRepository
    from src.services.tasks_management_service import TasksManagementService

    SessionLocal = get_session_factory()

    from src.api.config import get_settings

    settings = get_settings()

    with SessionLocal() as session:
        try:
            jobs_repo = SQLJobsRepository(session=session)
            service = TasksManagementService(
                jobs_repo=jobs_repo,
                broker=celery_app,
                chain_expires_seconds=settings.CELERY_TASK_CHAIN_EXPIRES,
                event_driven_dispatch=settings.EVENT_DRIVEN_DISPATCH,
            )

            if expires_at:
                now = datetime.datetime.now(datetime.timezone.utc)
                if datetime.datetime.fromisoformat(expires_at) <= now:
                    logger.info(
                        "Task %s launch %s expired at %s — finalizing without execution",
                        task_id, launch_id, expires_at,
                    )
                    try:
                        service.expire_task(scope_id=scope_id, task_id=task_spec_id, launch_id=launch_uuid)
                    except (InvalidChangeTaskStatusOperation, LaunchNotFound):
                        logger.warning(
                            "Task %s launch %s already finalized or superseded, discarding stale expiry",
                            task_id, launch_id,
                        )
                        return
                    except RequiredTaskNotFinished:
                        logger.warning(
                            "Task %s launch %s expiry skipped — predecessor still in-flight (stop_run race)",
                            task_id, launch_id,
                        )
                        return
                    session.commit()
                    return

            try:
                service.start_task(scope_id=scope_id, task_id=task_spec_id, launch_id=launch_uuid)
            except InvalidChangeTaskStatusOperation:
                logger.warning("Duplicate or stale message for launch %s — discarding", launch_id)
                return
            status, logs = _run_handler(task_spec_id=task_spec_id, scope_id=scope_id, launch_id=launch_uuid)

            if logs:
                service.update_journal(scope_id=scope_id, task_id=task_spec_id, launch_id=launch_uuid, logs=logs)

            successors = []
            match status:
                case TaskHandleStatus.SUCCESS:
                    _, successors = service.finish_task(
                        scope_id=scope_id, task_id=task_spec_id, launch_id=launch_uuid, user=user
                    )
                case TaskHandleStatus.SKIP:
                    _, successors = service.skip_task(
                        scope_id=scope_id, task_id=task_spec_id, launch_id=launch_uuid, user=user
                    )
                case TaskHandleStatus.FAIL:
                    service.abort_task(scope_id=scope_id, task_id=task_spec_id, launch_id=launch_uuid, is_aborted=False)
                    raise TaskExecutionError(task_id=task_id, scope_id=scope_id, launch_id=launch_id)

            session.commit()
            try:
                service.dispatch_successors(successors=successors, scope_id=scope_id, user=user)
            except Exception as dispatch_err:
                logger.error(
                    "Dispatch failed after commit for scope %s — successors may need manual replay: %s",
                    scope_id,
                    dispatch_err,
                    exc_info=dispatch_err,
                )
        except TaskExecutionError:
            session.rollback()
            raise
        except Exception as err:
            session.rollback()
            logger.error("Unhandled error in task %s: %s", task_id, err, exc_info=err)
            try:
                with SessionLocal() as err_session:
                    service = TasksManagementService(
                        jobs_repo=SQLJobsRepository(session=err_session), broker=celery_app
                    )
                    service.abort_task(scope_id=scope_id, task_id=task_spec_id, launch_id=launch_uuid, is_aborted=False)
                    err_session.commit()
            except Exception:
                logger.error("Failed to mark task as failed after error", exc_info=True)
            raise

    logger.info("Finished task %s launch %s", task_id, launch_id)


def _run_handler(
    task_spec_id: TaskSpecificationId, scope_id: str, launch_id: UUID
) -> tuple[TaskHandleStatus, list[Log]]:
    handler_cls = _HANDLERS.get(task_spec_id)
    if handler_cls is None:
        record = UnclassifiedLogRecord(
            message=f"No handler for task '{task_spec_id.value}'. Launch will be skipped.",
            timestamp=datetime.datetime.now(),
            level=LogLevel.ERROR,
        )
        logger.warning(str(record))
        return TaskHandleStatus.SKIP, [record]
    return handler_cls().run(scope_id=scope_id)
