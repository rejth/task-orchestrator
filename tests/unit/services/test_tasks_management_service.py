"""Unit tests for TasksManagementService feature-flag routing."""
from unittest.mock import MagicMock, patch

import pytest

from src.domain.job import ScopedJob
from src.domain.scoped_task import ScheduledScopedTask, StartedScopedTask, SuccessfullyFinishedScopedTask
from src.domain.task import TaskSpecificationId
from src.services.tasks_management_service import TasksManagementService
from tests.unit.domain.conftest import AT, JOB_ID, make_new_task, make_scheduled_task, make_spec


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


def _make_job_stub(scope_id: str, dispatchable) -> MagicMock:
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


# --- Task 3: dispatch successors on success and skip ---

T = TaskSpecificationId


def _make_started_task(spec) -> StartedScopedTask:
    return make_scheduled_task(spec).start(message="started", at=AT)


def _make_job_with_tasks(tasks) -> ScopedJob:
    scope = MagicMock()
    scope.get_id.return_value = SCOPE_ID
    return ScopedJob(id=JOB_ID, scope=scope, tasks=tasks)


def test_finish_task_event_driven_schedules_and_dispatches_successor(jobs_repo, broker):
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    started_a = _make_started_task(spec_a)
    new_b = make_new_task(spec_b)
    job = _make_job_with_tasks([started_a, new_b])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)

    _, successors = svc.finish_task(scope_id=SCOPE_ID, task_id=T.RELOAD_PATIENT_DATA, launch_id=started_a.current_launch.id, user=USER)

    assert len(successors) == 1
    assert successors[0].spec_id == T.RELOAD_SOMATIC_MUTATIONS
    assert isinstance(successors[0], ScheduledScopedTask)
    assert jobs_repo.update_task.call_count == 2

    svc.dispatch_successors(successors=successors, scope_id=SCOPE_ID, user=USER)
    mock_dispatcher.dispatch.assert_called_once_with(tasks=successors, scope_id=SCOPE_ID, user=USER)


def test_skip_task_event_driven_schedules_and_dispatches_successor(jobs_repo, broker):
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    started_a = _make_started_task(spec_a)
    new_b = make_new_task(spec_b)
    job = _make_job_with_tasks([started_a, new_b])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)

    _, successors = svc.skip_task(scope_id=SCOPE_ID, task_id=T.RELOAD_PATIENT_DATA, launch_id=started_a.current_launch.id, user=USER)

    assert len(successors) == 1
    assert successors[0].spec_id == T.RELOAD_SOMATIC_MUTATIONS
    assert isinstance(successors[0], ScheduledScopedTask)

    svc.dispatch_successors(successors=successors, scope_id=SCOPE_ID, user=USER)
    mock_dispatcher.dispatch.assert_called_once_with(tasks=successors, scope_id=SCOPE_ID, user=USER)


def test_finish_task_canvas_no_successor_dispatch(jobs_repo, broker):
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    started_a = _make_started_task(spec_a)
    new_b = make_new_task(spec_b)
    job = _make_job_with_tasks([started_a, new_b])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=False, task_dispatcher=mock_dispatcher)

    _, successors = svc.finish_task(scope_id=SCOPE_ID, task_id=T.RELOAD_PATIENT_DATA, launch_id=started_a.current_launch.id, user=USER)

    assert successors == []
    assert jobs_repo.update_task.call_count == 1
    svc.dispatch_successors(successors=successors, scope_id=SCOPE_ID, user=USER)
    mock_dispatcher.dispatch.assert_not_called()


def test_finish_task_event_driven_fan_in_not_ready(jobs_repo, broker):
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS)
    spec_c = make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA, T.RELOAD_SOMATIC_MUTATIONS])
    started_a = _make_started_task(spec_a)
    started_b = _make_started_task(spec_b)
    new_c = make_new_task(spec_c)
    job = _make_job_with_tasks([started_a, started_b, new_c])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)

    _, successors = svc.finish_task(scope_id=SCOPE_ID, task_id=T.RELOAD_PATIENT_DATA, launch_id=started_a.current_launch.id, user=USER)

    assert successors == []
    svc.dispatch_successors(successors=successors, scope_id=SCOPE_ID, user=USER)
    mock_dispatcher.dispatch.assert_not_called()


def test_dispatch_successors_empty_list_is_noop(jobs_repo, broker):
    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)
    svc.dispatch_successors(successors=[], scope_id=SCOPE_ID, user=USER)
    mock_dispatcher.dispatch.assert_not_called()


# --- Task 4: failure dispatches nothing; exactly-once fan-in ---

def _make_finished_task(spec) -> SuccessfullyFinishedScopedTask:
    return _make_started_task(spec).finish(message="finished", at=AT)


def test_abort_task_event_driven_dispatches_nothing_downstream(jobs_repo, broker):
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS, depends_on=[T.RELOAD_PATIENT_DATA])
    started_a = _make_started_task(spec_a)
    new_b = make_new_task(spec_b)
    job = _make_job_with_tasks([started_a, new_b])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)

    svc.abort_task(
        scope_id=SCOPE_ID,
        task_id=T.RELOAD_PATIENT_DATA,
        launch_id=started_a.current_launch.id,
        is_aborted=True,
    )

    mock_dispatcher.dispatch.assert_not_called()


def test_fan_in_last_predecessor_completes_dispatches_successor(jobs_repo, broker):
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS)
    spec_c = make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA, T.RELOAD_SOMATIC_MUTATIONS])
    finished_a = _make_finished_task(spec_a)
    started_b = _make_started_task(spec_b)
    new_c = make_new_task(spec_c)
    job = _make_job_with_tasks([finished_a, started_b, new_c])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)

    _, successors = svc.finish_task(
        scope_id=SCOPE_ID,
        task_id=T.RELOAD_SOMATIC_MUTATIONS,
        launch_id=started_b.current_launch.id,
        user=USER,
    )

    assert len(successors) == 1
    assert successors[0].spec_id == T.RELOAD_MATCHED_TREATMENTS
    assert isinstance(successors[0], ScheduledScopedTask)
    svc.dispatch_successors(successors=successors, scope_id=SCOPE_ID, user=USER)
    mock_dispatcher.dispatch.assert_called_once_with(tasks=successors, scope_id=SCOPE_ID, user=USER)


def test_fan_in_exactly_once_successor_already_pending_not_redispatched(jobs_repo, broker):
    """Concurrent worker already scheduled the successor: lock-based exactly-once prevents double dispatch."""
    spec_a = make_spec(T.RELOAD_PATIENT_DATA)
    spec_b = make_spec(T.RELOAD_SOMATIC_MUTATIONS)
    spec_c = make_spec(T.RELOAD_MATCHED_TREATMENTS, depends_on=[T.RELOAD_PATIENT_DATA, T.RELOAD_SOMATIC_MUTATIONS])
    finished_a = _make_finished_task(spec_a)
    started_b = _make_started_task(spec_b)
    # C is already PENDING — a concurrent worker scheduled it under the lock
    already_scheduled_c = make_scheduled_task(spec_c)
    job = _make_job_with_tasks([finished_a, started_b, already_scheduled_c])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=True, task_dispatcher=mock_dispatcher)

    _, successors = svc.finish_task(
        scope_id=SCOPE_ID,
        task_id=T.RELOAD_SOMATIC_MUTATIONS,
        launch_id=started_b.current_launch.id,
        user=USER,
    )

    assert successors == []
    svc.dispatch_successors(successors=successors, scope_id=SCOPE_ID, user=USER)
    mock_dispatcher.dispatch.assert_not_called()
