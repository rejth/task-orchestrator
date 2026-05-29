import os
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import src.infrastructure.database.models  # noqa: F401 — registers all ORM models in Base.metadata
from src.api.app import create_app
from src.api.deps import get_db, get_service, verify_api_key
from src.domain.job import OperationResult
from src.infrastructure.database.base import Base
from src.infrastructure.repositories.jobs_repo import SQLJobsRepository
from src.services.tasks_management_service import TasksManagementService

TEST_API_KEY = "test-key"
TEST_DATABASE_URL = "sqlite:///:memory:"


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("API_KEY", TEST_API_KEY)


class _NoQueueService(TasksManagementService):
    """Service subclass that skips actual Celery dispatch in tests."""

    def send_to_queue(self, result: OperationResult, user: str) -> None:
        pass


@pytest.fixture(scope="session")
def engine():
    e = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    yield e
    Base.metadata.drop_all(bind=e)


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
            db_session.flush()
        except Exception:
            db_session.rollback()
            raise

    def override_get_service() -> _NoQueueService:
        jobs_repo = SQLJobsRepository(session=db_session)
        return _NoQueueService(jobs_repo=jobs_repo, broker=MagicMock())

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_service] = override_get_service
    app.dependency_overrides[verify_api_key] = lambda: TEST_API_KEY

    with TestClient(app, headers={"X-API-Key": TEST_API_KEY}) as c:
        yield c
