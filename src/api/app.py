import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from src.api.config import get_settings
from src.api.deps import verify_api_key
from src.api.routers.tasks import router as tasks_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    logger.info("Starting task-orchestrator in '%s' environment", settings.ENVIRONMENT)
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Task Orchestrator",
        description="DAG-based task runner with state machines and Celery dispatch",
        version="1.0.0",
        lifespan=lifespan,
        dependencies=[Depends(verify_api_key)],
    )
    app.include_router(tasks_router)
    return app


app = create_app()
