import json
from uuid import UUID

from task_orchestrator.domain.journal import FileLogRecord, LogType, UnclassifiedLogRecord
from task_orchestrator.domain.task import TaskSpecificationId
from task_orchestrator.handlers.demo import build_demo_handler_registry, demo_task_runtime_seconds
from task_orchestrator.handlers.interface import TaskHandleStatus
from task_orchestrator.infrastructure.celery.runner import _run_handler


def test_demo_handler_registry_covers_every_task_specification():
    """The demo handler registry provides a handler for every TaskSpecificationId."""
    registry = build_demo_handler_registry()

    assert set(registry) == set(TaskSpecificationId)


def test_demo_handler_returns_journal_and_file_log_without_delay():
    """A demo handler with zero runtime returns SUCCESS, text logs, and one JSON file log."""
    registry = build_demo_handler_registry()
    handler = registry[TaskSpecificationId.RELOAD_PATIENT_DATA](0)

    status, logs = handler.run(scope_id="scope-123")

    assert status is TaskHandleStatus.SUCCESS
    assert any(isinstance(log, UnclassifiedLogRecord) for log in logs)
    file_logs = [log for log in logs if isinstance(log, FileLogRecord)]
    assert len(file_logs) == 1
    assert file_logs[0].type is LogType.FILE
    assert json.loads(file_logs[0].data)["task_id"] == "RELOAD_PATIENT_DATA"


def test_run_handler_uses_registered_demo_handler():
    """_run_handler delegates to the demo registry and returns SUCCESS with a file log."""
    status, logs = _run_handler(
        task_spec_id=TaskSpecificationId.EXPORT_TREATMENTS,
        scope_id="scope-123",
        launch_id=UUID("11111111-1111-1111-1111-111111111111"),
        min_runtime_seconds=0,
        max_runtime_seconds=0,
    )

    assert status is TaskHandleStatus.SUCCESS
    assert any(log.type is LogType.FILE for log in logs)


def test_demo_task_runtime_is_stable_within_bounds():
    """demo_task_runtime_seconds is deterministic and stays within min/max bounds."""
    first = demo_task_runtime_seconds(TaskSpecificationId.PUSH_THERAPY_NODE, 10, 15)
    second = demo_task_runtime_seconds(TaskSpecificationId.PUSH_THERAPY_NODE, 10, 15)

    assert first == second
    assert 10 <= first <= 15
