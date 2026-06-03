from __future__ import annotations

import datetime
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, replace
from enum import Enum
from queue import Queue
from typing import Callable, Generic, Protocol, Sequence, TypeVar
from uuid import UUID

from src.domain.journal import FileLogRecord, LaunchLogRecord, Log
from src.domain.scoped_task import (
    FailedScopedTask,
    LaunchNotFound,
    NewScopedTask,
    ScheduledScopedTask,
    ScopedTask,
    SkippedScopedTask,
    StartedScopedTask,
    SuccessfullyFinishedScopedTask,
)
from src.domain.task import TaskSpecification, TaskSpecificationId

logger = logging.getLogger(__name__)

S = TypeVar("S")

TaskDependencies = dict[TaskSpecificationId, list[TaskSpecificationId]]


class TaskLocation(Enum):
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    MULTIPLE = "MULTIPLE"


@dataclass(frozen=True)
class OperationResult(Generic[S]):
    updated_job: ScopedJobInterface[S]
    tasks_sequence: list[ScheduledScopedTask]


class InvalidChangeTaskStatusOperation(ValueError):
    def __init__(self, task: ScopedTask, operation: str):
        self.task = task
        self.operation = operation

    def __str__(self) -> str:
        return f"Can't '{self.operation}' task '{self.task.spec_id.value}' with status '{self.task.__class__.__name__}'"


class RequiredTaskNotFinished(ValueError):
    def __init__(self, target_task: ScopedTask, not_finished_task: ScopedTask):
        self.target_task = target_task
        self.not_finished_task = not_finished_task

    def __str__(self) -> str:
        return (
            f"Task '{self.target_task.spec_id.value}' can't be moved to next status, "
            f"because task '{self.not_finished_task.spec_id.value}' is not finished"
        )


class TaskIsNotStarted(ValueError):
    def __init__(self, task_id: TaskSpecificationId):
        self._task_id = task_id

    def __str__(self) -> str:
        return f"Task '{self._task_id.value}' is not started"


class TaskNotFound(ValueError):
    def __init__(self, task_id: TaskSpecificationId):
        self.task_id = task_id

    def __str__(self) -> str:
        return f"Task '{self.task_id.value}' was not found"


class ScopedJobInterface(Protocol[S]):
    def get_id(self) -> UUID: ...

    def get_scope(self) -> S: ...

    def get_tasks(self) -> Sequence[ScopedTask]: ...

    def schedule(
        self,
        task_id: TaskSpecificationId,
        launch_id_generator: Callable[[], UUID],
        message: str,
        at: datetime.datetime,
        by: str,
    ) -> OperationResult[S]: ...

    def start(
        self, task_id: TaskSpecificationId, launch_id: UUID, message: str, at: datetime.datetime
    ) -> tuple[ScopedJobInterface[S], StartedScopedTask]: ...

    def success(
        self, task_id: TaskSpecificationId, launch_id: UUID, message: str, at: datetime.datetime
    ) -> tuple[ScopedJobInterface[S], SuccessfullyFinishedScopedTask]: ...

    def fail(
        self,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        message: str,
        at: datetime.datetime,
        is_aborted: bool,
    ) -> ScopedJobInterface[S]: ...

    def skip(
        self, task_id: TaskSpecificationId, launch_id: UUID, message: str, at: datetime.datetime
    ) -> tuple[ScopedJobInterface[S], SkippedScopedTask]: ...

    def get_launch_journal(self, task_id: TaskSpecificationId, launch_id: UUID) -> Sequence[LaunchLogRecord]: ...

    def update_journal(
        self, task_id: TaskSpecificationId, launch_id: UUID, logs: list[Log]
    ) -> tuple[ScopedJobInterface[S], StartedScopedTask]: ...

    def get_log_file(self, task_id: TaskSpecificationId, launch_id: UUID, log_id: UUID) -> FileLogRecord: ...

    def dispatchable_tasks(self) -> list[ScheduledScopedTask]: ...

    def stop_run(self, message: str, at: datetime.datetime) -> tuple[ScopedJobInterface[S], list[UUID]]: ...


def _topological_sort(tasks: list[ScheduledScopedTask]) -> list[ScheduledScopedTask]:
    task_by_id = {t.spec_id: t for t in tasks}
    task_ids = set(task_by_id.keys())
    in_degree: dict[TaskSpecificationId, int] = {t.spec_id: 0 for t in tasks}
    for t in tasks:
        for dep_id in t.specification.depends_on:
            if dep_id in task_ids:
                in_degree[t.spec_id] += 1
    queue: Queue[TaskSpecificationId] = Queue()
    for spec_id, degree in in_degree.items():
        if degree == 0:
            queue.put(spec_id)
    sorted_tasks: list[ScheduledScopedTask] = []
    while not queue.empty():
        spec_id = queue.get()
        sorted_tasks.append(task_by_id[spec_id])
        for t in tasks:
            if spec_id in t.specification.depends_on and t.spec_id in task_ids:
                in_degree[t.spec_id] -= 1
                if in_degree[t.spec_id] == 0:
                    queue.put(t.spec_id)
    return sorted_tasks


@dataclass
class ScopedJob(Generic[S]):
    id: UUID
    scope: S
    tasks: Sequence[ScopedTask]

    def __hash__(self) -> int:
        return hash(self.id)

    def get_id(self) -> UUID:
        return self.id

    def get_scope(self) -> S:
        return self.scope

    def get_tasks(self) -> Sequence[ScopedTask]:
        return sorted(self.tasks, key=lambda item: item.spec_id.order)

    def get_launch_journal(self, task_id: TaskSpecificationId, launch_id: UUID) -> Sequence[LaunchLogRecord]:
        return self._get_task_by_id(task_id=task_id).get_journal(launch_id=launch_id)

    def get_log_file(self, task_id: TaskSpecificationId, launch_id: UUID, log_id: UUID) -> FileLogRecord:
        return self._get_task_by_id(task_id=task_id).get_log_file(launch_id=launch_id, log_id=log_id)

    def refresh(self, task_specifications: list[TaskSpecification]) -> ScopedJob[S]:
        if outstanding := self._get_outstanding_tasks():
            logger.warning("Can't refresh, outstanding tasks: %s", [t.spec_id.value for t in outstanding])
            return self
        return self._full_refresh(task_specifications=task_specifications)

    def schedule(
        self,
        task_id: TaskSpecificationId,
        launch_id_generator: Callable[[], UUID],
        message: str,
        at: datetime.datetime,
        by: str,
    ) -> OperationResult[S]:
        current_task = self._get_task_by_id(task_id=task_id)
        previous_tasks = self._previous_tasks(task=current_task)
        root_tasks = (
            [task for task in previous_tasks if len(task.specification.depends_on) == 0]
            if previous_tasks
            else [current_task]
        )

        tasks_to_schedule: set[TaskSpecificationId] = {current_task.spec_id}
        scoped_tasks: list[ScopedTask] = []

        for task in [*root_tasks, *self._next_tasks(start_tasks=root_tasks)]:
            scoped_tasks.append(task)
            match task:
                case NewScopedTask() | FailedScopedTask():
                    tasks_to_schedule.add(task.spec_id)

        task_graph = self._build_graph_dependencies(scoped_tasks=scoped_tasks)
        location_map = self._mark_graph(graph=task_graph, special_nodes=list(tasks_to_schedule))

        scheduled_sequence: list[ScheduledScopedTask] = []
        for spec_id, location in location_map.items():
            if location in (TaskLocation.MULTIPLE, TaskLocation.AFTER):
                scheduled_sequence.append(
                    self._schedule_current_task(
                        task_id=spec_id, launch_id=launch_id_generator(), message=message, at=at, by=by
                    )
                )

        sorted_sequence = _topological_sort(scheduled_sequence)
        return OperationResult[S](
            updated_job=self._update_tasks(tasks_to_update=sorted_sequence, new_tasks=[], deleted_tasks=set()),
            tasks_sequence=sorted_sequence,
        )

    def start(
        self,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        message: str,
        at: datetime.datetime,
    ) -> tuple[ScopedJob[S], StartedScopedTask]:
        target_task = self._get_task_by_id(task_id=task_id)
        self._validate_previous_tasks(task=target_task)
        match target_task:
            case ScheduledScopedTask(current_launch=current_launch) if current_launch.id == launch_id:
                started_task = target_task.start(message=message, at=at)
                return self._update_task(updated_task=started_task), started_task
        raise InvalidChangeTaskStatusOperation(task=target_task, operation="start")

    def success(
        self,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        message: str,
        at: datetime.datetime,
    ) -> tuple[ScopedJob[S], SuccessfullyFinishedScopedTask]:
        target_task = self._get_task_by_id(task_id=task_id)
        self._validate_previous_tasks(task=target_task)
        match target_task:
            case StartedScopedTask(current_launch=current_launch) if current_launch.id == launch_id:
                finished_task = target_task.finish(message=message, at=at)
                return self._update_task(updated_task=finished_task), finished_task
        raise InvalidChangeTaskStatusOperation(task=target_task, operation="success")

    def fail(
        self,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        message: str,
        at: datetime.datetime,
        is_aborted: bool,
    ) -> ScopedJob[S]:
        failed_current = self._fail_current_task(
            task_id=task_id, launch_id=launch_id, message=message, at=at, is_aborted=is_aborted
        )
        failed_next = self._fail_next_tasks(current_task=failed_current, message=message, at=at, is_aborted=is_aborted)
        return self._update_tasks(tasks_to_update=[failed_current, *failed_next], new_tasks=[], deleted_tasks=set())

    def skip(
        self,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        message: str,
        at: datetime.datetime,
    ) -> tuple[ScopedJob[S], SkippedScopedTask]:
        target_task = self._get_task_by_id(task_id=task_id)
        self._validate_previous_tasks(task=target_task)
        match target_task:
            case StartedScopedTask(current_launch=current_launch) if current_launch.id == launch_id:
                skipped_task = target_task.skip(message=message, at=at)
                return self._update_task(updated_task=skipped_task), skipped_task
        raise InvalidChangeTaskStatusOperation(task=target_task, operation="skip")

    def update_journal(
        self,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        logs: list[Log],
    ) -> tuple[ScopedJob[S], StartedScopedTask]:
        task = self._get_task_by_id(task_id=task_id)
        match task:
            case StartedScopedTask():
                started_task = task.update_journal(launch_id=launch_id, logs=logs)
                return self._update_task(updated_task=started_task), started_task
        raise TaskIsNotStarted(task_id=task_id)

    def _get_task_by_id(self, task_id: TaskSpecificationId) -> ScopedTask:
        for task in self.tasks:
            if task.spec_id is task_id:
                return task
        raise TaskNotFound(task_id=task_id)

    def _validate_previous_tasks(self, task: ScopedTask) -> None:
        for item in self._previous_tasks(task=task):
            match item:
                case ScheduledScopedTask() | StartedScopedTask() | FailedScopedTask():
                    raise RequiredTaskNotFinished(target_task=task, not_finished_task=item)

    def _schedule_current_task(
        self,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        message: str,
        at: datetime.datetime,
        by: str,
    ) -> ScheduledScopedTask:
        task = self._get_task_by_id(task_id=task_id)
        match task:
            case NewScopedTask():
                return task.schedule(launch_id=launch_id, message=message, at=at, by=by)
            case SuccessfullyFinishedScopedTask() | SkippedScopedTask() | FailedScopedTask():
                return task.reschedule(launch_id=launch_id, message=message, at=at, by=by)
        raise InvalidChangeTaskStatusOperation(task=task, operation="schedule")

    def _fail_current_task(
        self,
        task_id: TaskSpecificationId,
        launch_id: UUID,
        message: str,
        is_aborted: bool,
        at: datetime.datetime,
    ) -> FailedScopedTask:
        current_task = self._get_task_by_id(task_id=task_id)
        for task in self._previous_tasks(task=current_task):
            match task:
                case ScheduledScopedTask() | StartedScopedTask():
                    raise RequiredTaskNotFinished(target_task=current_task, not_finished_task=task)
        match current_task:
            case (
                ScheduledScopedTask(current_launch=current_launch) | StartedScopedTask(current_launch=current_launch)
            ) if current_launch.id == launch_id:
                return current_task.fail(message=message, at=at, is_aborted=is_aborted)
            case FailedScopedTask() | SuccessfullyFinishedScopedTask() | SkippedScopedTask():
                raise InvalidChangeTaskStatusOperation(task=current_task, operation="fail")
            case NewScopedTask():
                raise InvalidChangeTaskStatusOperation(task=current_task, operation="fail")
        raise LaunchNotFound(task_id=current_task.spec_id, launch_id=launch_id)

    def _fail_next_tasks(
        self,
        current_task: FailedScopedTask,
        message: str,
        is_aborted: bool,
        at: datetime.datetime,
    ) -> list[FailedScopedTask]:
        failed_tasks = []
        for task in self._next_tasks(start_tasks=[current_task]):
            match task:
                case NewScopedTask():
                    failed_tasks.append(task.fail(message=message, at=at, is_aborted=is_aborted))
                case ScheduledScopedTask() | StartedScopedTask():
                    failed_tasks.append(task.fail(message=message, at=at, is_aborted=is_aborted))
        return failed_tasks

    def _previous_tasks(self, task: ScopedTask) -> list[ScopedTask]:
        queue: Queue[ScopedTask] = Queue()
        visited: set[TaskSpecificationId] = set()
        previous_tasks: list[ScopedTask] = []

        def visit(item: ScopedTask) -> None:
            visited.add(item.spec_id)
            previous_tasks.append(item)
            queue.put(item)

        visited.add(task.spec_id)
        queue.put(task)

        while not queue.empty():
            first_task = queue.get()
            required = [self._get_task_by_id(task_id=tid) for tid in first_task.specification.depends_on]
            for elem in required:
                if elem.spec_id not in visited:
                    visit(elem)

        return previous_tasks[::-1]

    def _next_tasks(self, start_tasks: list[ScopedTask]) -> list[ScopedTask]:
        queue = deque(start_tasks)
        visited: set[TaskSpecificationId] = {t.spec_id for t in start_tasks}
        next_tasks: list[ScopedTask] = []

        def visit(item: ScopedTask) -> None:
            visited.add(item.spec_id)
            next_tasks.append(item)
            queue.append(item)

        while queue:
            first_task = queue.popleft()
            for elem in self.tasks:
                if elem.is_dependent(task_id=first_task.spec_id) and elem.spec_id not in visited:
                    visit(elem)

        return next_tasks

    def _update_tasks(
        self,
        tasks_to_update: Sequence[ScopedTask],
        new_tasks: Sequence[ScopedTask],
        deleted_tasks: set[TaskSpecificationId],
    ) -> ScopedJob[S]:
        updated: list[ScopedTask] = []
        for task in self.tasks:
            if task.spec_id in deleted_tasks:
                continue
            matched = next((u for u in tasks_to_update if u.match(task_id=task.spec_id)), None)
            updated.append(matched if matched else task)
        return replace(self, tasks=updated + list(new_tasks))

    def _update_task(self, updated_task: ScopedTask) -> ScopedJob[S]:
        return replace(self, tasks=[updated_task if updated_task.match(task_id=t.spec_id) else t for t in self.tasks])

    def dispatchable_tasks(self) -> list[ScheduledScopedTask]:
        """PENDING tasks whose every predecessor is SUCCESS or SKIPPED — runnable now."""
        task_by_id = {t.spec_id: t for t in self.tasks}
        result = []
        for task in self.get_tasks():
            if not isinstance(task, ScheduledScopedTask):
                continue
            if all(
                isinstance(task_by_id.get(pred_id), (SuccessfullyFinishedScopedTask, SkippedScopedTask))
                for pred_id in task.specification.depends_on
            ):
                result.append(task)
        return result

    def stop_run(self, message: str, at: datetime.datetime) -> tuple[ScopedJob[S], list[UUID]]:
        """Abort all PENDING and IN_PROGRESS tasks; return launch IDs to revoke in Celery."""
        aborted_tasks: list[ScopedTask] = []
        launch_ids: list[UUID] = []
        for task in self.tasks:
            match task:
                case NewScopedTask():
                    aborted_tasks.append(task.fail(message=message, at=at, is_aborted=True))
                case ScheduledScopedTask():
                    aborted_tasks.append(task.fail(message=message, at=at, is_aborted=True))
                    launch_ids.append(task.current_launch.id)
                case StartedScopedTask():
                    aborted_tasks.append(task.fail(message=message, at=at, is_aborted=True))
                    launch_ids.append(task.current_launch.id)
        updated_job = self._update_tasks(tasks_to_update=aborted_tasks, new_tasks=[], deleted_tasks=set())
        return updated_job, launch_ids

    def _get_outstanding_tasks(self) -> list[ScopedTask]:
        return [t for t in self.get_tasks() if isinstance(t, ScheduledScopedTask | StartedScopedTask)]

    def _full_refresh(self, task_specifications: list[TaskSpecification]) -> ScopedJob[S]:
        task_specs_by_id = {t.id: t for t in task_specifications}
        existing_by_spec_id = {t.spec_id: t for t in self.get_tasks()}
        existing_ids = set(existing_by_spec_id)
        full_ids = {t.id for t in task_specifications}
        return self._update_tasks(
            tasks_to_update=[existing_by_spec_id[sid].merge(task_specs_by_id[sid]) for sid in full_ids & existing_ids],
            new_tasks=[
                NewScopedTask.instance_of_specification(job_id=self.get_id(), specification=task_specs_by_id[sid])
                for sid in full_ids - existing_ids
            ],
            deleted_tasks=existing_ids - full_ids,
        )

    def _mark_graph(
        self,
        graph: TaskDependencies,
        special_nodes: list[TaskSpecificationId],
    ) -> dict[TaskSpecificationId, TaskLocation]:
        location_map: dict[TaskSpecificationId, TaskLocation] = {}
        reverse_graph: TaskDependencies = defaultdict(list)
        for spec_id, neighbors in graph.items():
            for neighbor in neighbors:
                reverse_graph[neighbor].append(spec_id)
        self._bfs_mark_task(reverse_graph, special_nodes, TaskLocation.BEFORE, location_map)
        self._bfs_mark_task(graph, special_nodes, TaskLocation.AFTER, location_map)
        return location_map

    @staticmethod
    def _bfs_mark_task(
        graph: TaskDependencies,
        start_nodes: list[TaskSpecificationId],
        location: TaskLocation,
        location_map: dict[TaskSpecificationId, TaskLocation],
    ) -> None:
        queue = deque(start_nodes)
        visited = set(start_nodes)
        while queue:
            current = queue.popleft()
            if current not in location_map:
                location_map[current] = location
            elif location_map[current] != location:
                location_map[current] = TaskLocation.MULTIPLE
            for neighbor in graph[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

    @staticmethod
    def _build_graph_dependencies(scoped_tasks: list[ScopedTask]) -> TaskDependencies:
        deps = {}
        for task in scoped_tasks:
            spec_id = task.spec_id
            deps[spec_id] = [t.spec_id for t in scoped_tasks if spec_id in t.specification.depends_on]
        return deps
