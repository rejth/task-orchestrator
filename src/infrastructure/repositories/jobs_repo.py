from __future__ import annotations

import logging
from typing import Optional, cast
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, selectinload

from src.domain.job import ScopedJob, ScopedJobInterface
from src.domain.journal import (
    FileLogRecord,
    LaunchLogRecord,
    LogType,
    UnclassifiedLogRecord,
)
from src.domain.launch import (
    FailedLaunch,
    FailMetadata,
    FinishedLaunch,
    ProgressMetadata,
    ScheduledLaunch,
    ScheduleMetadata,
    SkipMetadata,
    SkippedLaunch,
    StartedLaunch,
    SuccessfullyFinishedLaunch,
    SuccessMetadata,
    TaskLaunch,
    TaskLaunchStatus,
)
from src.domain.scope import Scope
from src.domain.scoped_task import (
    FailedScopedTask,
    NewScopedTask,
    ScheduledScopedTask,
    ScopedTask,
    ScopedTaskStatus,
    SkippedScopedTask,
    StartedScopedTask,
    SuccessfullyFinishedScopedTask,
)
from src.domain.task import TaskSpecification, TaskSpecificationId
from src.infrastructure.database.models.jobs import JobModel
from src.infrastructure.database.models.journal import ExecutionLogRecordModel, LogFileModel
from src.infrastructure.database.models.launches import TaskLaunchModel
from src.infrastructure.database.models.scoped_tasks import ScopedTaskModel

logger = logging.getLogger(__name__)


# ── domain ← model mappers ────────────────────────────────────────────────────

def _log_record_to_domain(model: ExecutionLogRecordModel) -> LaunchLogRecord:
    if model.type == LogType.FILE and model.file:
        log = FileLogRecord(
            level=model.level,
            message=model.message,
            timestamp=model.timestamp,
            filename=model.file.filename,
            extension=model.file.extension,
            data=model.file.data,
        )
    else:
        log = UnclassifiedLogRecord(level=model.level, message=model.message, timestamp=model.timestamp)

    return LaunchLogRecord(id=model.id, launch_id=model.launch_id, log=log)


def _launch_to_domain(model: TaskLaunchModel, *, include_journal: bool = True) -> TaskLaunch:
    journal = [_log_record_to_domain(j) for j in model.journal] if include_journal else []
    base = {"id": model.id, "task_id": model.task_id, "message": model.message, "journal": journal}

    match model.status:
        case TaskLaunchStatus.PENDING:
            return ScheduledLaunch(
                **base,
                metadata=ScheduleMetadata(
                    scheduled_at=model.scheduled_at,
                    scheduled_by=model.scheduled_by,
                ),
            )
        case TaskLaunchStatus.IN_PROGRESS:
            assert model.started_at is not None
            return StartedLaunch(
                **base,
                metadata=ProgressMetadata(
                    scheduled_at=model.scheduled_at,
                    scheduled_by=model.scheduled_by,
                    started_at=model.started_at,
                ),
            )
        case TaskLaunchStatus.FINISHED:
            assert model.started_at is not None
            assert model.finished_at is not None
            return SuccessfullyFinishedLaunch(
                **base,
                metadata=SuccessMetadata(
                    scheduled_at=model.scheduled_at,
                    scheduled_by=model.scheduled_by,
                    started_at=model.started_at,
                    finished_at=model.finished_at,
                ),
            )
        case TaskLaunchStatus.FAILED:
            assert model.started_at is not None
            assert model.failed_at is not None
            return FailedLaunch(
                **base,
                metadata=FailMetadata(
                    scheduled_at=model.scheduled_at,
                    scheduled_by=model.scheduled_by,
                    started_at=model.started_at,
                    failed_at=model.failed_at,
                    is_aborted=model.is_aborted or False,
                ),
            )
        case TaskLaunchStatus.SKIPPED:
            assert model.started_at is not None
            assert model.skipped_at is not None
            return SkippedLaunch(
                **base,
                metadata=SkipMetadata(
                    scheduled_at=model.scheduled_at,
                    scheduled_by=model.scheduled_by,
                    started_at=model.started_at,
                    skipped_at=model.skipped_at,
                ),
            )

    raise ValueError(f"Unknown launch status: {model.status}")


def _task_spec_from_model(model: ScopedTaskModel) -> TaskSpecification:
    return TaskSpecification(
        id=TaskSpecificationId(model.spec_id),
        label=model.label,
        description=model.description,
        depends_on=[TaskSpecificationId(d) for d in model.depends_on],
    )


def _task_to_domain(model: ScopedTaskModel, *, lightweight: bool = False) -> ScopedTask:
    spec = _task_spec_from_model(model)
    history: list[FinishedLaunch] = (
        []
        if lightweight
        else cast(list[FinishedLaunch], [_launch_to_domain(launch) for launch in model.launch_history])
    )

    match model.status:
        case ScopedTaskStatus.NEW:
            return NewScopedTask(
                id=model.id,
                job_id=model.job_id,
                specification=spec,
            )
        case ScopedTaskStatus.PENDING:
            assert model.current_launch is not None
            current = _launch_to_domain(model.current_launch, include_journal=not lightweight)
            assert isinstance(current, ScheduledLaunch)
            return ScheduledScopedTask(
                id=model.id,
                job_id=model.job_id,
                specification=spec,
                launch_history=history,
                current_launch=current,
            )
        case ScopedTaskStatus.IN_PROGRESS:
            assert model.current_launch is not None
            current = _launch_to_domain(model.current_launch, include_journal=not lightweight)
            assert isinstance(current, StartedLaunch)
            return StartedScopedTask(
                id=model.id,
                job_id=model.job_id,
                specification=spec,
                launch_history=history,
                current_launch=current,
            )
        case ScopedTaskStatus.SUCCESS:
            assert model.latest_launch is not None
            latest = _launch_to_domain(model.latest_launch, include_journal=not lightweight)
            assert isinstance(latest, SuccessfullyFinishedLaunch)
            return SuccessfullyFinishedScopedTask(
                id=model.id,
                job_id=model.job_id,
                specification=spec,
                launch_history=history,
                latest_launch=latest,
            )
        case ScopedTaskStatus.FAILED:
            assert model.latest_launch is not None
            latest = _launch_to_domain(model.latest_launch, include_journal=not lightweight)
            assert isinstance(latest, FailedLaunch)
            return FailedScopedTask(
                id=model.id,
                job_id=model.job_id,
                specification=spec,
                launch_history=history,
                latest_launch=latest,
            )
        case ScopedTaskStatus.SKIPPED:
            assert model.latest_launch is not None
            latest = _launch_to_domain(model.latest_launch, include_journal=not lightweight)
            assert isinstance(latest, SkippedLaunch)
            return SkippedScopedTask(
                id=model.id,
                job_id=model.job_id,
                specification=spec,
                launch_history=history,
                latest_launch=latest,
            )

    raise ValueError(f"Unknown task status: {model.status}")


# ── model ← domain mappers ────────────────────────────────────────────────────

def _apply_launch_to_model(launch: TaskLaunch, model: TaskLaunchModel) -> None:
    model.status = launch.status
    match launch:
        case ScheduledLaunch():
            model.scheduled_at = launch.metadata.scheduled_at
            model.scheduled_by = launch.metadata.scheduled_by
            model.started_at = None
            model.finished_at = None
            model.failed_at = None
            model.is_aborted = None
            model.skipped_at = None
        case StartedLaunch():
            model.started_at = launch.metadata.started_at
        case SuccessfullyFinishedLaunch():
            model.started_at = launch.metadata.started_at
            model.finished_at = launch.metadata.finished_at
        case FailedLaunch():
            model.started_at = launch.metadata.started_at
            model.failed_at = launch.metadata.failed_at
            model.is_aborted = launch.metadata.is_aborted
        case SkippedLaunch():
            model.started_at = launch.metadata.started_at
            model.skipped_at = launch.metadata.skipped_at


def _create_launch_model(launch: TaskLaunch) -> TaskLaunchModel:
    model = TaskLaunchModel(
        id=launch.id,
        task_id=launch.task_id,
        message=launch.message,
        status=launch.status,
        scheduled_at=launch.scheduled_at,
        scheduled_by=launch.scheduled_by,
    )
    _apply_launch_to_model(launch, model)
    return model


# ── repository ────────────────────────────────────────────────────────────────

class SQLJobsRepository:
    def __init__(self, session: Session):
        self._session = session

    def create_job(self, scope_id: str, task_specs: list[TaskSpecification]) -> None:
        job_id = uuid4()
        job_model = JobModel(id=job_id, scope_id=scope_id)
        task_models = [
            ScopedTaskModel(
                id=uuid4(),
                spec_id=spec.id.value,
                job_id=job_id,
                label=spec.label,
                description=spec.description,
                depends_on=[task_id.value for task_id in spec.depends_on],
                status=ScopedTaskStatus.NEW,
                current_launch_id=None,
                latest_launch_id=None,
            )
            for spec in task_specs
        ]
        self._session.add(job_model)

        for task_model in task_models:
            self._session.add(task_model)

        self._session.flush()

    def update(self, job: ScopedJobInterface) -> None:
        for task in job.get_tasks():
            self._persist_task(task)
        self._session.flush()

    def update_task(self, task: ScopedTask) -> None:
        self._persist_task(task)
        self._session.flush()

    def find_by_scope_id(self, scope_id: str) -> Optional[ScopedJobInterface]:
        return self._load(scope_id, for_update=False)

    def find_by_scope_id_for_update(self, scope_id: str) -> Optional[ScopedJobInterface]:
        return self._load(scope_id, for_update=True)

    def commit(self) -> None:
        self._session.commit()

    def delete(self, job_id: UUID) -> None:
        model = self._session.get(JobModel, job_id)
        if model:
            self._session.delete(model)
            self._session.flush()

    def list_all(self) -> list[ScopedJobInterface]:
        models = (
            self._session.query(JobModel)
            .filter(JobModel.tasks.any(ScopedTaskModel.status == ScopedTaskStatus.PENDING))
            .options(
                selectinload(JobModel.tasks).options(
                    selectinload(ScopedTaskModel.current_launch),
                    selectinload(ScopedTaskModel.latest_launch),
                )
            )
            .all()
        )
        jobs: list[ScopedJobInterface] = []
        for m in models:
            try:
                tasks = [_task_to_domain(t, lightweight=True) for t in m.tasks]
                jobs.append(ScopedJob(id=m.id, scope=Scope(scope_id=m.scope_id), tasks=tasks))
            except Exception:
                logger.error("Failed to hydrate job %s, skipping", m.id, exc_info=True)
        return jobs

    # ── internal ──────────────────────────────────────────────────────────────

    def _load(self, scope_id: str, for_update: bool) -> Optional[ScopedJobInterface]:
        query = self._session.query(JobModel).filter(JobModel.scope_id == scope_id)
        if for_update:
            query = query.with_for_update()

        model = query.first()
        if not model:
            return None

        scope = Scope(scope_id=model.scope_id)
        tasks = [_task_to_domain(task) for task in model.tasks]
        return ScopedJob(id=model.id, scope=scope, tasks=tasks)

    def _persist_task(self, task: ScopedTask) -> None:
        model = self._session.get(ScopedTaskModel, task.id)
        if not model:
            logger.warning("ScopedTaskModel %s not found during persist", task.id)
            return

        model.label = task.specification.label
        model.description = task.specification.description
        model.depends_on = [task_id.value for task_id in task.specification.depends_on]

        match task:
            case NewScopedTask():
                model.current_launch_id = None
                model.latest_launch_id = None

            case ScheduledScopedTask() | StartedScopedTask():
                launch = task.current_launch
                launch_model = self._session.get(TaskLaunchModel, launch.id)
                if launch_model is None:
                    launch_model = _create_launch_model(launch)
                    self._session.add(launch_model)
                    self._session.flush()  # insert launch before FK update on scoped_task
                else:
                    _apply_launch_to_model(launch, launch_model)
                model.current_launch_id = launch.id
                model.latest_launch_id = None
                # Persist journal for StartedScopedTask
                if isinstance(task, StartedScopedTask):
                    self._sync_journal(launch_model, task.current_launch)

            case SuccessfullyFinishedScopedTask() | FailedScopedTask() | SkippedScopedTask():
                launch = task.latest_launch
                launch_model = self._session.get(TaskLaunchModel, launch.id)
                if launch_model is None:
                    launch_model = _create_launch_model(launch)
                    self._session.add(launch_model)
                    self._session.flush()  # insert launch before FK update on scoped_task
                else:
                    _apply_launch_to_model(launch, launch_model)
                model.current_launch_id = None
                model.latest_launch_id = launch.id

        # set status last so CHECK constraint sees consistent launch FK state
        model.status = task.status

    def _sync_journal(self, launch_model: TaskLaunchModel, launch: StartedLaunch) -> None:
        existing_ids = {log_record.id for log_record in launch_model.journal}
        for log_record in launch.journal:
            if log_record.id in existing_ids:
                continue
            log = log_record.log
            entry = ExecutionLogRecordModel(
                id=log_record.id,
                launch_id=log_record.launch_id,
                message=log.message,
                timestamp=log.timestamp,
                level=log.level,
                type=log.type,
            )
            self._session.add(entry)
            if isinstance(log, FileLogRecord):
                self._session.add(LogFileModel(
                    log_id=log_record.id,
                    filename=log.filename,
                    extension=log.extension,
                    data=log.data,
                ))
