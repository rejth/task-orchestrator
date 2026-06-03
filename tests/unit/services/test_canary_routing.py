"""Unit tests for canary scope routing in TasksManagementService."""

from unittest.mock import MagicMock, patch

import pytest

from src.domain.job import ScopedJob
from src.domain.scoped_task import ScheduledScopedTask
from src.domain.task import TaskSpecificationId
from src.services.tasks_management_service import TasksManagementService
from tests.unit.domain.conftest import AT, JOB_ID, make_scheduled_task, make_spec

CANARY_SCOPE = "scope-in-canary"
REGULAR_SCOPE = "scope-not-in-canary"
USER = "svc@example.com"
CANARY_SET = frozenset([CANARY_SCOPE])


def _make_service(jobs_repo, broker, *, event_driven: bool = False, canary_scopes: frozenset = frozenset(), task_dispatcher=None) -> TasksManagementService:
    return TasksManagementService(
        jobs_repo=jobs_repo,
        broker=broker,
        event_driven_dispatch=event_driven,
        canary_scopes=canary_scopes,
        task_dispatcher=task_dispatcher,
    )


def _make_result(scope_id: str) -> MagicMock:
    scope = MagicMock()
    scope.get_id.return_value = scope_id
    job = MagicMock()
    job.get_scope.return_value = scope
    result = MagicMock()
    result.updated_job = job
    return result


@pytest.fixture
def jobs_repo():
    return MagicMock()


@pytest.fixture
def broker():
    return MagicMock()


# --- canary scope routes to event-driven even when global flag is off ---

def test_canary_scope_routes_to_event_driven(jobs_repo, broker):
    svc = _make_service(jobs_repo, broker, event_driven=False, canary_scopes=CANARY_SET)
    result = _make_result(CANARY_SCOPE)
    with patch.object(svc, "_send_to_canvas") as canvas, patch.object(svc, "_send_event_driven") as ed:
        svc.send_to_queue(result=result, user=USER)
    ed.assert_called_once_with(result, USER)
    canvas.assert_not_called()


def test_non_canary_scope_routes_to_canvas_when_flag_off(jobs_repo, broker):
    svc = _make_service(jobs_repo, broker, event_driven=False, canary_scopes=CANARY_SET)
    result = _make_result(REGULAR_SCOPE)
    with patch.object(svc, "_send_to_canvas") as canvas, patch.object(svc, "_send_event_driven") as ed:
        svc.send_to_queue(result=result, user=USER)
    canvas.assert_called_once_with(result, USER)
    ed.assert_not_called()


def test_global_flag_on_routes_all_scopes_to_event_driven(jobs_repo, broker):
    svc = _make_service(jobs_repo, broker, event_driven=True, canary_scopes=frozenset())
    result = _make_result(REGULAR_SCOPE)
    with patch.object(svc, "_send_to_canvas") as canvas, patch.object(svc, "_send_event_driven") as ed:
        svc.send_to_queue(result=result, user=USER)
    ed.assert_called_once()
    canvas.assert_not_called()


def test_empty_canary_set_no_canary_routing(jobs_repo, broker):
    svc = _make_service(jobs_repo, broker, event_driven=False, canary_scopes=frozenset())
    result = _make_result(CANARY_SCOPE)
    with patch.object(svc, "_send_to_canvas") as canvas, patch.object(svc, "_send_event_driven") as ed:
        svc.send_to_queue(result=result, user=USER)
    canvas.assert_called_once()
    ed.assert_not_called()


def test_canary_scope_also_routes_to_event_driven_when_global_flag_on(jobs_repo, broker):
    svc = _make_service(jobs_repo, broker, event_driven=True, canary_scopes=CANARY_SET)
    result = _make_result(CANARY_SCOPE)
    with patch.object(svc, "_send_to_canvas") as canvas, patch.object(svc, "_send_event_driven") as ed:
        svc.send_to_queue(result=result, user=USER)
    ed.assert_called_once()
    canvas.assert_not_called()


# --- canary scope schedules successors on finish/skip ---

def _make_started_task(spec):
    return make_scheduled_task(spec).start(message="started", at=AT)


def _make_job_with_tasks(scope_id: str, tasks) -> ScopedJob:
    scope = MagicMock()
    scope.get_id.return_value = scope_id
    return ScopedJob(id=JOB_ID, scope=scope, tasks=tasks)


def test_canary_scope_finish_task_schedules_successors(jobs_repo, broker):
    spec_a = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    spec_b = make_spec(TaskSpecificationId.RELOAD_SOMATIC_MUTATIONS, depends_on=[TaskSpecificationId.RELOAD_PATIENT_DATA])
    started_a = _make_started_task(spec_a)
    scheduled_b = make_scheduled_task(spec_b)
    job = _make_job_with_tasks(CANARY_SCOPE, [started_a, scheduled_b])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=False, canary_scopes=CANARY_SET, task_dispatcher=mock_dispatcher)

    _, successors = svc.finish_task(
        scope_id=CANARY_SCOPE,
        task_id=TaskSpecificationId.RELOAD_PATIENT_DATA,
        launch_id=started_a.current_launch.id,
        user=USER,
    )

    assert len(successors) == 1
    assert isinstance(successors[0], ScheduledScopedTask)
    assert successors[0].spec_id == TaskSpecificationId.RELOAD_SOMATIC_MUTATIONS


def test_non_canary_scope_finish_task_no_successors(jobs_repo, broker):
    spec_a = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    spec_b = make_spec(TaskSpecificationId.RELOAD_SOMATIC_MUTATIONS, depends_on=[TaskSpecificationId.RELOAD_PATIENT_DATA])
    started_a = _make_started_task(spec_a)
    scheduled_b = make_scheduled_task(spec_b)
    job = _make_job_with_tasks(REGULAR_SCOPE, [started_a, scheduled_b])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=False, canary_scopes=CANARY_SET, task_dispatcher=mock_dispatcher)

    _, successors = svc.finish_task(
        scope_id=REGULAR_SCOPE,
        task_id=TaskSpecificationId.RELOAD_PATIENT_DATA,
        launch_id=started_a.current_launch.id,
        user=USER,
    )

    assert successors == []


def test_canary_scope_skip_task_schedules_successors(jobs_repo, broker):
    spec_a = make_spec(TaskSpecificationId.RELOAD_PATIENT_DATA)
    spec_b = make_spec(TaskSpecificationId.RELOAD_SOMATIC_MUTATIONS, depends_on=[TaskSpecificationId.RELOAD_PATIENT_DATA])
    started_a = _make_started_task(spec_a)
    scheduled_b = make_scheduled_task(spec_b)
    job = _make_job_with_tasks(CANARY_SCOPE, [started_a, scheduled_b])
    jobs_repo.find_by_scope_id_for_update.return_value = job

    mock_dispatcher = MagicMock()
    svc = _make_service(jobs_repo, broker, event_driven=False, canary_scopes=CANARY_SET, task_dispatcher=mock_dispatcher)

    _, successors = svc.skip_task(
        scope_id=CANARY_SCOPE,
        task_id=TaskSpecificationId.RELOAD_PATIENT_DATA,
        launch_id=started_a.current_launch.id,
        user=USER,
    )

    assert len(successors) == 1
    assert isinstance(successors[0], ScheduledScopedTask)


def test_multiple_scopes_in_canary_set(jobs_repo, broker):
    multi_canary = frozenset(["scope-a", "scope-b", "scope-c"])
    for scope_id in ["scope-a", "scope-b", "scope-c"]:
        svc = _make_service(jobs_repo, broker, event_driven=False, canary_scopes=multi_canary)
        result = _make_result(scope_id)
        with patch.object(svc, "_send_to_canvas") as canvas, patch.object(svc, "_send_event_driven") as ed:
            svc.send_to_queue(result=result, user=USER)
        ed.assert_called_once()
        canvas.assert_not_called()
