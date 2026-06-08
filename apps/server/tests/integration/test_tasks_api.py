"""Integration tests for the tasks HTTP API."""

import datetime
import uuid
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from task_orchestrator.domain.journal import FileLogRecord, LogFileExtension, LogLevel, LogType
from task_orchestrator.domain.task import TaskSpecificationId
from task_orchestrator.infrastructure.repositories.jobs_repo import SQLJobsRepository
from task_orchestrator.services.tasks_management_service import TasksManagementService

TASK_COUNT = 24  # active demo tasks in task_specifications.yml
API_PREFIX = "/api"


def _scope_id() -> str:
    return str(uuid.uuid4())


def test_init_scope_creates_job(client: TestClient):
    scope_id = _scope_id()
    resp = client.post(f"{API_PREFIX}/scopes/{scope_id}")
    assert resp.status_code == 201
    assert resp.json()["scope_id"] == scope_id


def test_init_scope_twice_returns_409(client: TestClient):
    scope_id = _scope_id()
    client.post(f"{API_PREFIX}/scopes/{scope_id}")
    resp = client.post(f"{API_PREFIX}/scopes/{scope_id}")
    assert resp.status_code == 409


def test_get_tasks_returns_all_specs(client: TestClient):
    scope_id = _scope_id()
    client.post(f"{API_PREFIX}/scopes/{scope_id}")
    resp = client.get(f"{API_PREFIX}/scopes/{scope_id}/tasks")
    assert resp.status_code == 200
    tasks = resp.json()["tasks"]
    assert len(tasks) == TASK_COUNT
    spec_ids = {t["spec_id"] for t in tasks}
    assert "RELOAD_PATIENT_DATA" in spec_ids
    assert "REFRESH_INDEXES" in spec_ids


def test_get_tasks_for_unknown_scope_returns_404(client: TestClient):
    resp = client.get(f"{API_PREFIX}/scopes/{_scope_id()}/tasks")
    assert resp.status_code == 404


def test_schedule_task_returns_202_and_pending_tasks(client: TestClient):
    scope_id = _scope_id()
    client.post(f"{API_PREFIX}/scopes/{scope_id}")
    resp = client.post(
        f"{API_PREFIX}/scopes/{scope_id}/tasks/RELOAD_PATIENT_DATA/schedule",
    )
    assert resp.status_code == 202
    tasks = resp.json()["tasks"]
    assert all(t["status"] == "PENDING" for t in tasks)


def test_schedule_from_root_schedules_downstream(client: TestClient):
    scope_id = _scope_id()
    client.post(f"{API_PREFIX}/scopes/{scope_id}")
    resp = client.post(
        f"{API_PREFIX}/scopes/{scope_id}/tasks/RELOAD_PATIENT_DATA/schedule",
    )
    assert resp.status_code == 202
    scheduled_ids = {t["spec_id"] for t in resp.json()["tasks"]}
    assert "RELOAD_PATIENT_DATA" in scheduled_ids
    assert "RELOAD_MATCHED_TREATMENTS" in scheduled_ids
    assert "REFRESH_INDEXES" in scheduled_ids


def test_schedule_unknown_task_returns_422(client: TestClient):
    scope_id = _scope_id()
    client.post(f"{API_PREFIX}/scopes/{scope_id}")
    resp = client.post(f"{API_PREFIX}/scopes/{scope_id}/tasks/NOT_A_REAL_TASK/schedule")
    assert resp.status_code == 422


def test_abort_unknown_launch_returns_404(client: TestClient):
    scope_id = _scope_id()
    client.post(f"{API_PREFIX}/scopes/{scope_id}")
    client.post(f"{API_PREFIX}/scopes/{scope_id}/tasks/RELOAD_PATIENT_DATA/schedule")
    resp = client.delete(f"{API_PREFIX}/scopes/{scope_id}/tasks/RELOAD_PATIENT_DATA/launches/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_get_journal_for_nonexistent_launch_returns_404(client: TestClient):
    scope_id = _scope_id()
    client.post(f"{API_PREFIX}/scopes/{scope_id}")
    resp = client.get(f"{API_PREFIX}/scopes/{scope_id}/tasks/RELOAD_PATIENT_DATA/launches/{uuid.uuid4()}/journal")
    assert resp.status_code == 404


def test_file_logs_are_persisted(client: TestClient, db_session: Session):
    scope_id = _scope_id()
    client.post(f"{API_PREFIX}/scopes/{scope_id}")
    schedule_resp = client.post(f"{API_PREFIX}/scopes/{scope_id}/tasks/RELOAD_PATIENT_DATA/schedule")
    launch_id = uuid.UUID(schedule_resp.json()["tasks"][0]["current_launch"]["id"])

    service = TasksManagementService(
        jobs_repo=SQLJobsRepository(session=db_session),
        broker=MagicMock(),
    )
    task_id = TaskSpecificationId.RELOAD_PATIENT_DATA
    service.start_task(scope_id=scope_id, task_id=task_id, launch_id=launch_id)
    service.update_journal(
        scope_id=scope_id,
        task_id=task_id,
        launch_id=launch_id,
        logs=[
            FileLogRecord(
                message="Produced patient snapshot.",
                timestamp=datetime.datetime.now(datetime.timezone.utc),
                level=LogLevel.INFO,
                filename="patient-snapshot",
                extension=LogFileExtension.JSON,
                data=b'{"patient_id":"demo"}',
            )
        ],
    )
    db_session.commit()

    journal = service.get_journal(scope_id=scope_id, task_id=task_id, launch_id=launch_id)
    file_entry = next(entry for entry in journal if entry.log.type is LogType.FILE)
    stored_file = service.get_log_file(scope_id=scope_id, task_id=task_id, launch_id=launch_id, log_id=file_entry.id)

    assert stored_file.full_filename == "patient-snapshot.json"
    assert stored_file.data == b'{"patient_id":"demo"}'
