from __future__ import annotations

import datetime
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, replace
from enum import Enum
from typing import Sequence
from uuid import UUID, uuid4

from task_orchestrator.domain.journal import FileLogRecord, LaunchLogRecord, Log


class LogNotFound(ValueError):
    def __init__(self, log_id: UUID):
        self._log_id = log_id

    def __str__(self) -> str:
        return f"Log '{self._log_id}' was not found"


class TaskLaunchStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class BaseTaskLaunch(metaclass=ABCMeta):
    id: UUID
    task_id: UUID
    message: str
    journal: Sequence[LaunchLogRecord]

    def __hash__(self) -> int:
        return hash(self.id)

    def get_log_file(self, log_id: UUID) -> FileLogRecord:
        for item in self.journal:
            log_data = item.log
            match log_data:
                case FileLogRecord() if item.id == log_id:
                    return log_data
        raise LogNotFound(log_id=log_id)

    @property
    def full_work_time(self) -> datetime.timedelta:
        return datetime.datetime.now() - self.scheduled_at

    @property
    @abstractmethod
    def status(self) -> TaskLaunchStatus: ...

    @property
    @abstractmethod
    def scheduled_at(self) -> datetime.datetime: ...

    @property
    @abstractmethod
    def scheduled_by(self) -> str: ...


@dataclass(frozen=True)
class ScheduleMetadata:
    scheduled_at: datetime.datetime
    scheduled_by: str


@dataclass(frozen=True)
class ProgressMetadata(ScheduleMetadata):
    started_at: datetime.datetime


@dataclass(frozen=True)
class SuccessMetadata(ProgressMetadata):
    finished_at: datetime.datetime


@dataclass(frozen=True)
class FailMetadata(ProgressMetadata):
    failed_at: datetime.datetime
    is_aborted: bool


@dataclass(frozen=True)
class SkipMetadata(ProgressMetadata):
    skipped_at: datetime.datetime


@dataclass(frozen=True)
class ScheduledLaunch(BaseTaskLaunch):
    metadata: ScheduleMetadata

    @property
    def status(self) -> TaskLaunchStatus:
        return TaskLaunchStatus.PENDING

    @property
    def scheduled_at(self) -> datetime.datetime:
        return self.metadata.scheduled_at

    @property
    def scheduled_by(self) -> str:
        return self.metadata.scheduled_by

    def start(self, message: str, at: datetime.datetime) -> StartedLaunch:
        return StartedLaunch(
            task_id=self.task_id,
            id=self.id,
            message=message,
            journal=self.journal,
            metadata=ProgressMetadata(
                scheduled_at=self.metadata.scheduled_at,
                scheduled_by=self.metadata.scheduled_by,
                started_at=at,
            ),
        )

    def fail(self, message: str, at: datetime.datetime, is_aborted: bool) -> FailedLaunch:
        return FailedLaunch(
            task_id=self.task_id,
            id=self.id,
            message=message,
            journal=self.journal,
            metadata=FailMetadata(
                scheduled_at=self.metadata.scheduled_at,
                scheduled_by=self.metadata.scheduled_by,
                started_at=at,
                failed_at=at,
                is_aborted=is_aborted,
            ),
        )


@dataclass(frozen=True)
class StartedLaunch(BaseTaskLaunch):
    metadata: ProgressMetadata

    @property
    def status(self) -> TaskLaunchStatus:
        return TaskLaunchStatus.IN_PROGRESS

    @property
    def scheduled_at(self) -> datetime.datetime:
        return self.metadata.scheduled_at

    @property
    def scheduled_by(self) -> str:
        return self.metadata.scheduled_by

    def update_journal(self, logs: list[Log]) -> StartedLaunch:
        return replace(self, journal=list(self.journal) + [self._make_log(log=log) for log in logs])

    def success(self, message: str, at: datetime.datetime) -> SuccessfullyFinishedLaunch:
        return SuccessfullyFinishedLaunch(
            task_id=self.task_id,
            id=self.id,
            message=message,
            journal=self.journal,
            metadata=SuccessMetadata(
                scheduled_at=self.scheduled_at,
                scheduled_by=self.metadata.scheduled_by,
                started_at=self.metadata.started_at,
                finished_at=at,
            ),
        )

    def fail(self, message: str, at: datetime.datetime, is_aborted: bool) -> FailedLaunch:
        return FailedLaunch(
            task_id=self.task_id,
            id=self.id,
            message=message,
            journal=self.journal,
            metadata=FailMetadata(
                scheduled_at=self.scheduled_at,
                scheduled_by=self.metadata.scheduled_by,
                started_at=self.metadata.started_at,
                failed_at=at,
                is_aborted=is_aborted,
            ),
        )

    def skip(self, message: str, at: datetime.datetime) -> SkippedLaunch:
        return SkippedLaunch(
            task_id=self.task_id,
            id=self.id,
            message=message,
            journal=self.journal,
            metadata=SkipMetadata(
                scheduled_at=self.scheduled_at,
                scheduled_by=self.metadata.scheduled_by,
                started_at=self.metadata.started_at,
                skipped_at=at,
            ),
        )

    def _make_log(self, log: Log) -> LaunchLogRecord:
        return LaunchLogRecord(id=uuid4(), launch_id=self.id, log=log)


@dataclass(frozen=True)
class SuccessfullyFinishedLaunch(BaseTaskLaunch):
    metadata: SuccessMetadata

    @property
    def status(self) -> TaskLaunchStatus:
        return TaskLaunchStatus.FINISHED

    @property
    def scheduled_at(self) -> datetime.datetime:
        return self.metadata.scheduled_at

    @property
    def scheduled_by(self) -> str:
        return self.metadata.scheduled_by

    @property
    def execution_time(self) -> datetime.timedelta:
        return self.metadata.finished_at - self.metadata.started_at

    @property
    def full_work_time(self) -> datetime.timedelta:
        return self.metadata.finished_at - self.metadata.scheduled_at


@dataclass(frozen=True)
class FailedLaunch(BaseTaskLaunch):
    metadata: FailMetadata

    @property
    def status(self) -> TaskLaunchStatus:
        return TaskLaunchStatus.FAILED

    @property
    def scheduled_at(self) -> datetime.datetime:
        return self.metadata.scheduled_at

    @property
    def scheduled_by(self) -> str:
        return self.metadata.scheduled_by


@dataclass(frozen=True)
class SkippedLaunch(BaseTaskLaunch):
    metadata: SkipMetadata

    @property
    def status(self) -> TaskLaunchStatus:
        return TaskLaunchStatus.SKIPPED

    @property
    def scheduled_at(self) -> datetime.datetime:
        return self.metadata.scheduled_at

    @property
    def scheduled_by(self) -> str:
        return self.metadata.scheduled_by


FinishedLaunch = SuccessfullyFinishedLaunch | FailedLaunch | SkippedLaunch
TaskLaunch = ScheduledLaunch | StartedLaunch | SuccessfullyFinishedLaunch | FailedLaunch | SkippedLaunch
