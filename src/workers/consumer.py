"""Celery worker entry point.

Start with:
    celery -A src.workers.consumer worker --loglevel=info
"""
import src.infrastructure.celery.runner  # noqa: F401 — registers the task_runner task
import src.infrastructure.celery.sweep_task  # noqa: F401 — registers the reconciliation_sweep task
from src.infrastructure.celery.app import get_celery_app

app = get_celery_app()
