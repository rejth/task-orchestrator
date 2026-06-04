"""Celery periodic task that runs the reconciliation sweep."""

import logging

from src.api.config import get_settings
from src.infrastructure.celery.app import get_celery_app
from src.infrastructure.database.session import get_session_factory
from src.infrastructure.repositories.jobs_repo import SQLJobsRepository
from src.services.reconciliation_sweep_service import ReconciliationSweepService
from src.services.task_dispatcher import TaskDispatcher

logger = logging.getLogger(__name__)

SWEEP_TASK_NAME = "reconciliation_sweep"

celery_app = get_celery_app()


@celery_app.task(name=SWEEP_TASK_NAME)
def reconciliation_sweep() -> None:
    settings = get_settings()
    SessionLocal = get_session_factory()

    with SessionLocal() as session:
        jobs_repo = SQLJobsRepository(session=session)
        dispatcher = TaskDispatcher(
            broker=celery_app,
            expiry_seconds=settings.TASK_EXPIRY_SECONDS,
        )
        service = ReconciliationSweepService(
            jobs_repo=jobs_repo,
            dispatcher=dispatcher,
            system_user="system@sweep",
        )
        try:
            service.sweep()
        except Exception:
            logger.exception("Reconciliation sweep failed")
            raise

    logger.info("Reconciliation sweep completed")
