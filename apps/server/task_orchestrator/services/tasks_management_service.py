import datetime
import logging
from typing import Sequence
from uuid import UUID, uuid4

from celery import Celery

from task_orchestrator.domain.job import InvalidChangeTaskStatusOperation, OperationResult, ScopedJobInterface
from task_orchestrator.domain.jobs_repo import JobsRepository
from task_orchestrator.domain.journal import FileLogRecord, LaunchLogRecord, Log
from task_orchestrator.domain.scoped_task import (
    ScheduledScopedTask,
    ScopedTask,
    SkippedScopedTask,
    StartedScopedTask,
    SuccessfullyFinishedScopedTask,
)
from task_orchestrator.domain.task import TaskSpecification, TaskSpecificationId
from task_orchestrator.services.task_dispatcher import TaskDispatcher

logger = logging.getLogger(__name__)


class JobNotFound(ValueError):
    def __init__(self, scope_id: str):
        self._scope_id = scope_id

    def __str__(self) -> str:
        return f"Job for scope '{self._scope_id}' was not found"


class TasksManagementService:
    def __init__(
        self,
        jobs_repo: JobsRepository,
        broker: Celery,
        task_dispatcher: TaskDispatcher | None = None,
    ):
        self._jobs_repo = jobs_repo
        self._broker = broker
        self._dispatcher = task_dispatcher or TaskDispatcher(broker=broker, expiry_seconds=3600)

    def create_job(self, scope_id: str, task_specs: list[TaskSpecification]) -> None:
        self._jobs_repo.create_job(scope_id=scope_id, task_specs=task_specs)

    def get_tasks(self, scope_id: str) -> Sequence[ScopedTask]:
        return self._require_job(scope_id).get_tasks()

    def schedule_task(self, scope_id: str, task_id: TaskSpecificationId, user: str) -> OperationResult:
        job = self._require_job_for_update(scope_id)
        result = job.schedule(
            task_id=task_id,
            launch_id_generator=uuid4,
            message="Task was scheduled",
            at=datetime.datetime.now(datetime.timezone.utc),
            by=user,
        )
        self._jobs_repo.update(job=result.updated_job)
        return result

    def send_to_queue(self, result: OperationResult, user: str) -> None:
        self._send_event_driven(result, user)

    def _send_event_driven(self, result: OperationResult, user: str) -> None:
        tasks = result.updated_job.dispatchable_tasks()
        scope_id = result.updated_job.get_scope().get_id()
        self._dispatcher.dispatch(tasks=tasks, scope_id=scope_id, user=user)

    def start_task(self, scope_id: str, task_id: TaskSpecificationId, launch_id: UUID) -> ScopedJobInterface:
        job = self._require_job_for_update(scope_id)
        updated_job, started_task = job.start(
            task_id=task_id,
            launch_id=launch_id,
            message="Task was started",
            at=datetime.datetime.now(datetime.timezone.utc),
        )
        self._jobs_repo.update_task(task=started_task)
        return updated_job

    def finish_task(
        self,
        scope_id: str,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        user: str = "",
    ) -> tuple[ScopedJobInterface, list[ScheduledScopedTask]]:
        job = self._require_job_for_update(scope_id)
        updated_job, finished_task = job.success(
            task_id=task_id,
            launch_id=launch_id,
            message="Task was successfully finished",
            at=datetime.datetime.now(datetime.timezone.utc),
        )
        self._jobs_repo.update_task(task=finished_task)
        successors = self._schedule_unblocked_successors(updated_job, user, task_id)
        return updated_job, successors

    def abort_task(
        self,
        scope_id: str,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        is_aborted: bool,
    ) -> ScopedJobInterface:
        job = self._require_job_for_update(scope_id)
        updated_job = job.fail(
            task_id=task_id,
            launch_id=launch_id,
            message="Task was aborted",
            at=datetime.datetime.now(datetime.timezone.utc),
            is_aborted=is_aborted,
        )
        self._jobs_repo.update(job=updated_job)
        return updated_job

    def skip_task(
        self,
        scope_id: str,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        user: str = "",
    ) -> tuple[ScopedJobInterface, list[ScheduledScopedTask]]:
        job = self._require_job_for_update(scope_id)
        updated_job, skipped_task = job.skip(
            task_id=task_id,
            launch_id=launch_id,
            message="Task was skipped",
            at=datetime.datetime.now(datetime.timezone.utc),
        )
        self._jobs_repo.update_task(task=skipped_task)
        successors = self._schedule_unblocked_successors(updated_job, user, task_id)
        return updated_job, successors

    def expire_task(
        self,
        scope_id: str,
        task_id: TaskSpecificationId,
        launch_id: UUID,
    ) -> ScopedJobInterface:
        job = self._require_job_for_update(scope_id)
        for task in job.get_tasks():
            if task.spec_id is task_id and isinstance(task, StartedScopedTask):
                if task.current_launch.id == launch_id:
                    # Task already started by another worker — stale expiry, discard it.
                    raise InvalidChangeTaskStatusOperation(task=task, operation="expire")
                break
        updated_job = job.fail(
            task_id=task_id,
            launch_id=launch_id,
            message="Task expired while waiting in queue",
            at=datetime.datetime.now(datetime.timezone.utc),
            is_aborted=True,
        )
        self._jobs_repo.update(job=updated_job)
        return updated_job

    def stop_run(self, scope_id: str) -> None:
        job = self._require_job_for_update(scope_id)
        updated_job, launch_ids = job.stop_run(
            message="Run was stopped",
            at=datetime.datetime.now(datetime.timezone.utc),
        )
        self._jobs_repo.update(job=updated_job)
        self._jobs_repo.commit()
        for launch_id in launch_ids:
            try:
                self._broker.control.revoke(str(launch_id), terminate=True)
            except Exception:
                logger.warning("Failed to revoke Celery task %s — worker may still execute", launch_id, exc_info=True)

    def dispatch_successors(self, successors: list[ScheduledScopedTask], scope_id: str, user: str) -> None:
        if successors:
            self._dispatcher.dispatch(tasks=successors, scope_id=scope_id, user=user)

    def _schedule_unblocked_successors(
        self, updated_job: ScopedJobInterface, user: str, completed_task_id: TaskSpecificationId
    ) -> list[ScheduledScopedTask]:
        task_by_id = {t.spec_id: t for t in updated_job.get_tasks()}
        scheduled = []
        for task in updated_job.get_tasks():
            if not isinstance(task, ScheduledScopedTask):
                continue
            if completed_task_id not in task.specification.depends_on:
                continue
            if all(
                isinstance(task_by_id.get(pred_id), (SuccessfullyFinishedScopedTask, SkippedScopedTask))
                for pred_id in task.specification.depends_on
            ):
                scheduled.append(task)
        return scheduled

    def update_journal(
        self,
        scope_id: str,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        logs: list[Log],
    ) -> ScopedJobInterface:
        job = self._require_job_for_update(scope_id)
        updated_job, started_task = job.update_journal(task_id=task_id, launch_id=launch_id, logs=logs)
        self._jobs_repo.update_task(task=started_task)
        return updated_job

    def get_journal(self, scope_id: str, task_id: TaskSpecificationId, launch_id: UUID) -> Sequence[LaunchLogRecord]:
        return self._require_job(scope_id).get_launch_journal(task_id=task_id, launch_id=launch_id)

    def get_log_file(self, scope_id: str, task_id: TaskSpecificationId, launch_id: UUID, log_id: UUID) -> FileLogRecord:
        return self._require_job(scope_id).get_log_file(task_id=task_id, launch_id=launch_id, log_id=log_id)

    def _require_job(self, scope_id: str) -> ScopedJobInterface:
        job = self._jobs_repo.find_by_scope_id(scope_id=scope_id)
        if not job:
            raise JobNotFound(scope_id=scope_id)
        return job

    def _require_job_for_update(self, scope_id: str) -> ScopedJobInterface:
        job = self._jobs_repo.find_by_scope_id_for_update(scope_id=scope_id)
        if not job:
            raise JobNotFound(scope_id=scope_id)
        return job
