"""Celery worker entry point.

Start with:
    celery -A task_orchestrator.workers.consumer worker --loglevel=info
"""

import task_orchestrator.infrastructure.celery.runner  # noqa: F401 — registers the task_runner task
import task_orchestrator.infrastructure.celery.sweep_task  # noqa: F401 — registers the reconciliation_sweep task
from task_orchestrator.infrastructure.celery.app import get_celery_app

app = get_celery_app()
