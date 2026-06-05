from collections.abc import Generator

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from task_orchestrator.api.config import Settings, get_settings
from task_orchestrator.infrastructure.celery.app import get_celery_app
from task_orchestrator.infrastructure.database.session import get_session_factory
from task_orchestrator.infrastructure.repositories.jobs_repo import SQLJobsRepository
from task_orchestrator.infrastructure.repositories.tasks_repo import FsTaskSpecificationsRepo
from task_orchestrator.services.task_dispatcher import TaskDispatcher
from task_orchestrator.services.tasks_management_service import TasksManagementService

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def verify_api_key(
    api_key: str = Security(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


def get_db(settings: Settings = Depends(get_settings)) -> Generator[Session, None, None]:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_jobs_repo(db: Session = Depends(get_db)) -> SQLJobsRepository:
    return SQLJobsRepository(session=db)


def get_tasks_repo() -> FsTaskSpecificationsRepo:
    return FsTaskSpecificationsRepo()


def get_service(
    jobs_repo: SQLJobsRepository = Depends(get_jobs_repo),
    settings: Settings = Depends(get_settings),
) -> TasksManagementService:
    broker = get_celery_app(settings.REDIS_URL)
    return TasksManagementService(
        jobs_repo=jobs_repo,
        broker=broker,
        task_dispatcher=TaskDispatcher(broker=broker, expiry_seconds=settings.TASK_EXPIRY_SECONDS),
    )
