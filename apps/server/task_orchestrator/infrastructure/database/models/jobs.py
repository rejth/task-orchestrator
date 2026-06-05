from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

from task_orchestrator.infrastructure.database.base import Base
from task_orchestrator.infrastructure.database.models.scoped_tasks import ScopedTaskModel


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    scope_id: Mapped[str] = mapped_column(index=True, unique=True)

    tasks: Mapped[list[ScopedTaskModel]] = relationship(
        ScopedTaskModel,
        lazy="select",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
