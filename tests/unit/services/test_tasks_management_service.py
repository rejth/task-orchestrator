"""Unit tests for TasksManagementService feature-flag routing."""
from unittest.mock import MagicMock, patch

import pytest

from src.domain.task import TaskSpecificationId
from src.services.tasks_management_service import TasksManagementService
from tests.unit.domain.conftest import make_scheduled_task, make_spec


@pytest.fixture
def jobs_repo():
    return MagicMock()


@pytest.fixture
def broker():
    return MagicMock()


@pytest.fixture
def operation_result():
    return MagicMock()


def _make_service(
    jobs_repo,
    broker,
    event_driven: bool,
    task_dispatcher=None,
) -> TasksManagementService:
    return TasksManagementService(
        jobs_repo=jobs_repo,
        broker=broker,
        event_driven_dispatch=event_driven,
        task_dispatcher=task_dispatcher,
    )


def test_flag_off_routes_to_canvas(jobs_repo, broker, operation_result):
    svc = _make_service(jobs_repo, broker, event_driven=False)
    with patch.object(svc, "_send_to_canvas") as canvas_mock, \
         patch.object(svc, "_send_event_driven") as ed_mock:
        svc.send_to_queue(result=operation_result, user="user@example.com")
    canvas_mock.assert_called_once_with(operation_result, "user@example.com")
    ed_mock.assert_not_called()


def test_flag_on_routes_to_event_driven(jobs_repo, broker, operation_result):
    svc = _make_service(jobs_repo, broker, event_driven=True)
    with patch.object(svc, "_send_to_canvas") as canvas_mock, \
         patch.object(svc, "_send_event_driven") as ed_mock:
        svc.send_to_queue(result=operation_result, user="user@example.com")
    ed_mock.assert_called_once_with(operation_result, "user@example.com")
    canvas_mock.assert_not_called()


def test_default_flag_is_canvas(jobs_repo, broker, operation_result):
    svc = TasksManagementService(jobs_repo=jobs_repo, broker=broker)
    with patch.object(svc, "_send_to_canvas") as canvas_mock, \
         patch.object(svc, "_send_event_driven") as ed_mock:
        svc.send_to_queue(result=operation_result, user="user@example.com")
    canvas_mock.assert_called_once()
    ed_mock.assert_not_called()


# --- Task 2: event-driven schedule dispatches the ready frontier ---

SCOPE_ID = "patient-abc"
USER = "svc@example.com"


def _make_job_stub(scope_id: str, dispatchable):
    scope = MagicMock()
    scope.get_id.return_value = scope_id
    job = MagicMock()
    job.get_scope.return_value = scope
    job.dispatchable_tasks.return_value = dispatchable
    return job


def test_event_driven_dispatches_ready_frontier(jobs_repo, broker):
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    ready_task = make_scheduled_task(spec)
    job = _make_job_stub(SCOPE_ID, [ready_task])

    result = MagicMock()
    result.updated_job = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)
    svc.send_to_queue(result=result, user=USER)

    mock_dispatcher.dispatch.assert_called_once_with(tasks=[ready_task], scope_id=SCOPE_ID, user=USER)


def test_event_driven_empty_frontier_dispatches_nothing(jobs_repo, broker):
    job = _make_job_stub(SCOPE_ID, [])
    result = MagicMock()
    result.updated_job = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)
    svc.send_to_queue(result=result, user=USER)

    mock_dispatcher.dispatch.assert_called_once_with(tasks=[], scope_id=SCOPE_ID, user=USER)


def test_event_driven_passes_scope_id_from_job(jobs_repo, broker):
    expected_scope = "unique-scope-99"
    spec = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    job = _make_job_stub(expected_scope, [make_scheduled_task(spec)])
    result = MagicMock()
    result.updated_job = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)
    svc.send_to_queue(result=result, user=USER)

    _, kwargs = mock_dispatcher.dispatch.call_args
    assert kwargs["scope_id"] == expected_scope


def test_canvas_path_does_not_use_dispatcher(jobs_repo, broker, operation_result):
    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=False, task_dispatcher=mock_dispatcher)
    with patch.object(svc, "_send_to_canvas"):
        svc.send_to_queue(result=operation_result, user=USER)
    mock_dispatcher.dispatch.assert_not_called()
