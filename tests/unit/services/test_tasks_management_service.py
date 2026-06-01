"""Unit tests for TasksManagementService feature-flag routing."""
from unittest.mock import MagicMock, patch

import pytest

from src.services.tasks_management_service import TasksManagementService


@pytest.fixture
def jobs_repo():
    return MagicMock()


@pytest.fixture
def broker():
    return MagicMock()


@pytest.fixture
def operation_result():
    return MagicMock()


def _make_service(jobs_repo, broker, event_driven: bool) -> TasksManagementService:
    return TasksManagementService(
        jobs_repo=jobs_repo,
        broker=broker,
        event_driven_dispatch=event_driven,
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
