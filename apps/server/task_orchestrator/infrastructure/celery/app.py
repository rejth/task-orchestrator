from celery import Celery

_app: Celery | None = None


def get_celery_app(broker_url: str | None = None) -> Celery:
    global _app
    if _app is None:
        from task_orchestrator.api.config import get_settings

        settings = get_settings()
        url = broker_url or settings.REDIS_URL
        _app = Celery("task_orchestrator", broker=url, backend=url)
        _app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            beat_schedule={
                "reconciliation-sweep": {
                    "task": "reconciliation_sweep",
                    "schedule": settings.RECONCILIATION_SWEEP_INTERVAL_SECONDS,
                },
            },
        )
    return _app
