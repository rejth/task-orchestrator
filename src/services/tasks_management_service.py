import datetime
from typing import Sequence
from uuid import UUID, uuid4

from celery import Celery

from src.domain.job import OperationResult, ScopedJobInterface
from src.domain.jobs_repo import JobsRepository
from src.domain.journal import FileLogRecord, LaunchLogRecord, Log
from src.domain.scoped_task import ScopedTask
from src.domain.task import TaskSpecification, TaskSpecificationId
from src.services.make_celery_chain import CeleryChainBuilder


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
        chain_expires_seconds: int = 3600,
        event_driven_dispatch: bool = False,
    ):
        self._jobs_repo = jobs_repo
        self._broker = broker
        self._chain_expires_seconds = chain_expires_seconds
        self._event_driven_dispatch = event_driven_dispatch

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
            at=datetime.datetime.now(),
            by=user,
        )
        self._jobs_repo.update(job=result.updated_job)
        return result

    def send_to_queue(self, result: OperationResult, user: str) -> None:
        if self._event_driven_dispatch:
            self._send_event_driven(result, user)
        else:
            self._send_to_canvas(result, user)

    def _send_to_canvas(self, result: OperationResult, user: str) -> None:
        from typing import cast

        from src.services.make_task_graph import SequentialTasks

        builder = CeleryChainBuilder(result.updated_job, user, self._chain_expires_seconds, self._broker)
        builder.make_celery_chain(cast(SequentialTasks, result.task_graph)).apply_async()

    def _send_event_driven(self, result: OperationResult, user: str) -> None:
        pass

    def start_task(self, scope_id: str, task_id: TaskSpecificationId, launch_id: UUID) -> ScopedJobInterface:
        job = self._require_job_for_update(scope_id)
        updated_job, started_task = job.start(
            task_id=task_id,
            launch_id=launch_id,
            message="Task was started",
            at=datetime.datetime.now(),
        )
        self._jobs_repo.update_task(task=started_task)
        return updated_job

    def finish_task(self, scope_id: str, task_id: TaskSpecificationId, launch_id: UUID) -> ScopedJobInterface:
        job = self._require_job_for_update(scope_id)
        updated_job, finished_task = job.success(
            task_id=task_id,
            launch_id=launch_id,
            message="Task was successfully finished",
            at=datetime.datetime.now(),
        )
        self._jobs_repo.update_task(task=finished_task)
        return updated_job

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
            at=datetime.datetime.now(),
            is_aborted=is_aborted,
        )
        self._jobs_repo.update(job=updated_job)
        return updated_job

    def skip_task(self, scope_id: str, task_id: TaskSpecificationId, launch_id: UUID) -> ScopedJobInterface:
        job = self._require_job_for_update(scope_id)
        updated_job, skipped_task = job.skip(
            task_id=task_id,
            launch_id=launch_id,
            message="Task was skipped",
            at=datetime.datetime.now(),
        )
        self._jobs_repo.update_task(task=skipped_task)
        return updated_job

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
