from __future__ import annotations

import datetime
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, replace
from enum import Enum
from typing import Sequence
from uuid import UUID, uuid4

from src.domain.journal import FileLogRecord, LaunchLogRecord, Log
from src.domain.launch import (
    FailedLaunch,
    FailMetadata,
    FinishedLaunch,
    ScheduledLaunch,
    ScheduleMetadata,
    SkippedLaunch,
    StartedLaunch,
    SuccessfullyFinishedLaunch,
    TaskLaunch,
)
from src.domain.task import TaskSpecification, TaskSpecificationId


class LaunchNotFound(ValueError):
    def __init__(self, task_id: TaskSpecificationId, launch_id: UUID):
        self.task_id = task_id
        self.launch_id = launch_id

    def __str__(self) -> str:
        return f"Launch '{self.launch_id}' in task '{self.task_id.value}' was not found"


class LaunchIsNotCurrent(ValueError):
    def __init__(self, launch_id: UUID, current_launch_id: UUID):
        self._current_launch_id = current_launch_id
        self._launch_id = launch_id

    def __str__(self) -> str:
        return f"Launch '{self._launch_id}' is not current. Current launch is '{self._current_launch_id}'"


class ScopedTaskStatus(Enum):
    NEW = "NEW"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class BaseScopedTask(metaclass=ABCMeta):
    id: UUID
    job_id: UUID
    specification: TaskSpecification

    @property
    @abstractmethod
    def status(self) -> ScopedTaskStatus: ...

    def get_journal(self, launch_id: UUID) -> Sequence[LaunchLogRecord]:
        return self.get_launch_by_id(launch_id=launch_id).journal

    def get_log_file(self, launch_id: UUID, log_id: UUID) -> FileLogRecord:
        return self.get_launch_by_id(launch_id=launch_id).get_log_file(log_id=log_id)

    @abstractmethod
    def get_launch_by_id(self, launch_id: UUID) -> TaskLaunch: ...

    @property
    def spec_id(self) -> TaskSpecificationId:
        return self.specification.id

    def match(self, task_id: TaskSpecificationId) -> bool:
        return self.specification.match(task_id=task_id)

    def is_dependent(self, task_id: TaskSpecificationId) -> bool:
        return self.specification.is_dependent(task_id=task_id)

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class NewScopedTask(BaseScopedTask):
    @property
    def launch_history(self) -> list[TaskLaunch]:
        return []

    def get_launch_by_id(self, launch_id: UUID) -> TaskLaunch:
        raise LaunchNotFound(task_id=self.spec_id, launch_id=launch_id)

    def merge(self, updated: TaskSpecification) -> ScopedTask:
        return replace(self, specification=self.specification.merge(updated=updated))

    @classmethod
    def instance_of_specification(cls, job_id: UUID, specification: TaskSpecification) -> NewScopedTask:
        return cls(id=uuid4(), job_id=job_id, specification=specification)

    @property
    def status(self) -> ScopedTaskStatus:
        return ScopedTaskStatus.NEW

    def schedule(self, launch_id: UUID, message: str, at: datetime.datetime, by: str) -> ScheduledScopedTask:
        return ScheduledScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=[],
            current_launch=ScheduledLaunch(
                task_id=self.id,
                id=launch_id,
                message=message,
                journal=[],
                metadata=ScheduleMetadata(scheduled_at=at, scheduled_by=by),
            ),
        )

    def fail(self, message: str, at: datetime.datetime, is_aborted: bool) -> FailedScopedTask:
        return FailedScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=[],
            latest_launch=FailedLaunch(
                task_id=self.id,
                id=uuid4(),
                message=message,
                journal=[],
                metadata=FailMetadata(
                    scheduled_at=at,
                    scheduled_by="",
                    started_at=at,
                    failed_at=at,
                    is_aborted=is_aborted,
                ),
            ),
        )


@dataclass
class ScheduledScopedTask(BaseScopedTask):
    launch_history: Sequence[FinishedLaunch]
    current_launch: ScheduledLaunch

    def get_launch_by_id(self, launch_id: UUID) -> TaskLaunch:
        if self.current_launch.id == launch_id:
            return self.current_launch
        for launch in self.launch_history:
            if launch.id == launch_id:
                return launch
        raise LaunchNotFound(task_id=self.spec_id, launch_id=launch_id)

    def merge(self, updated: TaskSpecification) -> ScopedTask:
        return replace(self, specification=self.specification.merge(updated=updated))

    @property
    def status(self) -> ScopedTaskStatus:
        return ScopedTaskStatus.PENDING

    def start(self, message: str, at: datetime.datetime) -> StartedScopedTask:
        return StartedScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=self.launch_history,
            current_launch=self.current_launch.start(message=message, at=at),
        )

    def fail(self, message: str, at: datetime.datetime, is_aborted: bool) -> FailedScopedTask:
        return FailedScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=self.launch_history,
            latest_launch=self.current_launch.fail(message=message, at=at, is_aborted=is_aborted),
        )


@dataclass
class StartedScopedTask(BaseScopedTask):
    launch_history: Sequence[FinishedLaunch]
    current_launch: StartedLaunch

    def get_launch_by_id(self, launch_id: UUID) -> TaskLaunch:
        if self.current_launch.id == launch_id:
            return self.current_launch
        for launch in self.launch_history:
            if launch.id == launch_id:
                return launch
        raise LaunchNotFound(task_id=self.spec_id, launch_id=launch_id)

    def update_journal(self, launch_id: UUID, logs: list[Log]) -> StartedScopedTask:
        if self.current_launch.id != launch_id:
            raise LaunchIsNotCurrent(launch_id=launch_id, current_launch_id=self.current_launch.id)
        return replace(self, current_launch=self.current_launch.update_journal(logs=logs))

    def merge(self, updated: TaskSpecification) -> ScopedTask:
        return replace(self, specification=self.specification.merge(updated=updated))

    @property
    def status(self) -> ScopedTaskStatus:
        return ScopedTaskStatus.IN_PROGRESS

    def fail(self, message: str, at: datetime.datetime, is_aborted: bool) -> FailedScopedTask:
        return FailedScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=self.launch_history,
            latest_launch=self.current_launch.fail(message=message, at=at, is_aborted=is_aborted),
        )

    def finish(self, message: str, at: datetime.datetime) -> SuccessfullyFinishedScopedTask:
        return SuccessfullyFinishedScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=self.launch_history,
            latest_launch=self.current_launch.success(message=message, at=at),
        )

    def skip(self, message: str, at: datetime.datetime) -> SkippedScopedTask:
        return SkippedScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=self.launch_history,
            latest_launch=self.current_launch.skip(message=message, at=at),
        )


@dataclass
class SuccessfullyFinishedScopedTask(BaseScopedTask):
    launch_history: Sequence[FinishedLaunch]
    latest_launch: SuccessfullyFinishedLaunch

    def get_launch_by_id(self, launch_id: UUID) -> TaskLaunch:
        if self.latest_launch.id == launch_id:
            return self.latest_launch
        for launch in self.launch_history:
            if launch.id == launch_id:
                return launch
        raise LaunchNotFound(task_id=self.spec_id, launch_id=launch_id)

    def merge(self, updated: TaskSpecification) -> ScopedTask:
        return replace(self, specification=self.specification.merge(updated=updated))

    @property
    def status(self) -> ScopedTaskStatus:
        return ScopedTaskStatus.SUCCESS

    def reschedule(self, launch_id: UUID, message: str, at: datetime.datetime, by: str) -> ScheduledScopedTask:
        return ScheduledScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=[*self.launch_history[:8], self.latest_launch],
            current_launch=ScheduledLaunch(
                task_id=self.id,
                id=launch_id,
                message=message,
                journal=[],
                metadata=ScheduleMetadata(scheduled_at=at, scheduled_by=by),
            ),
        )


@dataclass
class FailedScopedTask(BaseScopedTask):
    launch_history: Sequence[FinishedLaunch]
    latest_launch: FailedLaunch

    def get_launch_by_id(self, launch_id: UUID) -> TaskLaunch:
        if self.latest_launch.id == launch_id:
            return self.latest_launch
        for launch in self.launch_history:
            if launch.id == launch_id:
                return launch
        raise LaunchNotFound(task_id=self.spec_id, launch_id=launch_id)

    def merge(self, updated: TaskSpecification) -> ScopedTask:
        return replace(self, specification=self.specification.merge(updated=updated))

    @property
    def status(self) -> ScopedTaskStatus:
        return ScopedTaskStatus.FAILED

    def reschedule(self, launch_id: UUID, message: str, at: datetime.datetime, by: str) -> ScheduledScopedTask:
        return ScheduledScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=[*self.launch_history[:8], self.latest_launch],
            current_launch=ScheduledLaunch(
                task_id=self.id,
                id=launch_id,
                message=message,
                journal=[],
                metadata=ScheduleMetadata(scheduled_at=at, scheduled_by=by),
            ),
        )


@dataclass
class SkippedScopedTask(BaseScopedTask):
    launch_history: Sequence[FinishedLaunch]
    latest_launch: SkippedLaunch

    def get_launch_by_id(self, launch_id: UUID) -> TaskLaunch:
        if self.latest_launch.id == launch_id:
            return self.latest_launch
        for launch in self.launch_history:
            if launch.id == launch_id:
                return launch
        raise LaunchNotFound(task_id=self.spec_id, launch_id=launch_id)

    def merge(self, updated: TaskSpecification) -> ScopedTask:
        return replace(self, specification=self.specification.merge(updated=updated))

    @property
    def status(self) -> ScopedTaskStatus:
        return ScopedTaskStatus.SKIPPED

    def reschedule(self, launch_id: UUID, message: str, at: datetime.datetime, by: str) -> ScheduledScopedTask:
        return ScheduledScopedTask(
            id=self.id,
            job_id=self.job_id,
            specification=self.specification,
            launch_history=[*self.launch_history[:8], self.latest_launch],
            current_launch=ScheduledLaunch(
                task_id=self.id,
                id=launch_id,
                message=message,
                journal=[],
                metadata=ScheduleMetadata(scheduled_at=at, scheduled_by=by),
            ),
        )


ScopedTask = (
    NewScopedTask
    | ScheduledScopedTask
    | StartedScopedTask
    | SuccessfullyFinishedScopedTask
    | FailedScopedTask
    | SkippedScopedTask
)
