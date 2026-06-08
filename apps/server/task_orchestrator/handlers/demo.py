"""Demo task handlers that simulate realistic work for every Task."""

from __future__ import annotations

import datetime
import hashlib
import json
import time
from dataclasses import dataclass
from functools import partial
from typing import Callable

from task_orchestrator.domain.journal import FileLogRecord, Log, LogFileExtension, LogLevel, UnclassifiedLogRecord
from task_orchestrator.domain.task import TaskSpecificationId
from task_orchestrator.handlers.interface import TaskHandleStatus


@dataclass(frozen=True)
class DemoTaskProfile:
    action: str
    subject: str
    steps: tuple[str, str, str]
    output_name: str


DemoTaskFactory = Callable[[float], "DemoHandler"]


class DemoHandler:
    def __init__(self, task_id: TaskSpecificationId, profile: DemoTaskProfile, runtime_seconds: float):
        self._task_id = task_id
        self._profile = profile
        self._runtime_seconds = max(0.0, runtime_seconds)

    def run(self, scope_id: str) -> tuple[TaskHandleStatus, list[Log]]:
        logs: list[Log] = [
            self._message(
                f"{self._profile.action} {self._profile.subject} for Scope {scope_id}.",
            )
        ]

        step_delay = self._runtime_seconds / len(self._profile.steps) if self._profile.steps else 0
        for step in self._profile.steps:
            if step_delay:
                time.sleep(step_delay)
            logs.append(self._message(step))

        logs.append(self._result_file(scope_id=scope_id))
        logs.append(self._message(f"{self._profile.output_name} is ready."))
        return TaskHandleStatus.SUCCESS, logs

    def _message(self, message: str, level: LogLevel = LogLevel.INFO) -> UnclassifiedLogRecord:
        return UnclassifiedLogRecord(
            message=message,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            level=level,
        )

    def _result_file(self, scope_id: str) -> FileLogRecord:
        payload = {
            "scope_id": scope_id,
            "task_id": self._task_id.value,
            "artifact": self._profile.output_name,
            "processed_records": _deterministic_record_count(scope_id=scope_id, task_id=self._task_id),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        return FileLogRecord(
            message=f"Produced demo artifact {self._profile.output_name}.json.",
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            level=LogLevel.INFO,
            filename=self._profile.output_name,
            extension=LogFileExtension.JSON,
            data=json.dumps(payload, indent=2, sort_keys=True).encode(),
        )


def build_demo_handler_registry() -> dict[TaskSpecificationId, DemoTaskFactory]:
    return {task_id: partial(DemoHandler, task_id, _profile_for_task(task_id)) for task_id in TaskSpecificationId}


def demo_task_runtime_seconds(task_id: TaskSpecificationId, min_seconds: float, max_seconds: float) -> float:
    minimum = max(0.0, min_seconds)
    maximum = max(minimum, max_seconds)
    if maximum == minimum:
        return minimum

    digest = hashlib.sha256(task_id.value.encode()).hexdigest()
    ratio = int(digest[:8], 16) / 0xFFFFFFFF
    return minimum + ((maximum - minimum) * ratio)


def _profile_for_task(task_id: TaskSpecificationId) -> DemoTaskProfile:
    subject = task_id.value.lower()
    readable_subject = subject.replace("_", " ")
    output_name = subject.replace("_", "-")

    if task_id.value.startswith("RELOAD_"):
        return DemoTaskProfile(
            action="Loading",
            subject=readable_subject,
            steps=(
                "Connected to the source data set.",
                "Validated source rows and normalized identifiers.",
                "Persisted refreshed Task data.",
            ),
            output_name=output_name,
        )
    if task_id.value.startswith("PULL_"):
        return DemoTaskProfile(
            action="Fetching",
            subject=readable_subject,
            steps=(
                "Opened external feed cursor.",
                "Fetched and de-duplicated remote records.",
                "Stored imported records for matching.",
            ),
            output_name=output_name,
        )
    if task_id.value.startswith("EXPORT_"):
        return DemoTaskProfile(
            action="Serialising",
            subject=readable_subject,
            steps=(
                "Collected upstream Task outputs.",
                "Rendered report payload fragments.",
                "Validated export schema.",
            ),
            output_name=output_name,
        )
    if task_id.value.startswith("PUSH_"):
        return DemoTaskProfile(
            action="Publishing",
            subject=readable_subject,
            steps=(
                "Prepared outbound payload.",
                "Submitted payload to the external report system.",
                "Recorded external acknowledgement.",
            ),
            output_name=output_name,
        )
    if task_id.value.startswith("SYNC_"):
        return DemoTaskProfile(
            action="Synchronising",
            subject=readable_subject,
            steps=(
                "Loaded local and remote snapshots.",
                "Calculated changes to apply.",
                "Committed synchronization checkpoint.",
            ),
            output_name=output_name,
        )
    if task_id.value.startswith("CREATE_") or task_id.value.startswith("SET_"):
        return DemoTaskProfile(
            action="Configuring",
            subject=readable_subject,
            steps=(
                "Loaded report configuration context.",
                "Applied deterministic demo defaults.",
                "Saved configuration output.",
            ),
            output_name=output_name,
        )

    return DemoTaskProfile(
        action="Processing",
        subject=readable_subject,
        steps=(
            "Resolved upstream Task outputs.",
            "Applied demo transformation rules.",
            "Stored Task output artifact.",
        ),
        output_name=output_name,
    )


def _deterministic_record_count(scope_id: str, task_id: TaskSpecificationId) -> int:
    digest = hashlib.sha256(f"{scope_id}:{task_id.value}".encode()).hexdigest()
    return 25 + (int(digest[:6], 16) % 975)
