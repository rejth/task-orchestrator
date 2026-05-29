from typing import Optional
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, ForeignKey, UniqueConstraint, and_, desc, or_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.launch import TaskLaunchStatus
from src.domain.scoped_task import ScopedTaskStatus
from src.infrastructure.database.base import Base
from src.infrastructure.database.models.launches import TaskLaunchModel


class ScopedTaskModel(Base):
    __tablename__ = "scoped_tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    spec_id: Mapped[str] = mapped_column(index=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    label: Mapped[str]
    description: Mapped[str]
    depends_on: Mapped[list[str]] = mapped_column(JSON)
    status: Mapped[ScopedTaskStatus] = mapped_column(index=True)

    current_launch_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("task_launches.id", use_alter=True), index=True
    )
    latest_launch_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("task_launches.id", use_alter=True), index=True
    )

    current_launch: Mapped[Optional[TaskLaunchModel]] = relationship(
        TaskLaunchModel, foreign_keys=[current_launch_id], uselist=False
    )
    latest_launch: Mapped[Optional[TaskLaunchModel]] = relationship(
        TaskLaunchModel, foreign_keys=[latest_launch_id], uselist=False
    )

    launch_history: Mapped[list[TaskLaunchModel]] = relationship(
        TaskLaunchModel,
        primaryjoin=and_(
            id == TaskLaunchModel.task_id,
            or_(
                and_(latest_launch_id.is_not(None), latest_launch_id != TaskLaunchModel.id),
                latest_launch_id.is_(None),
            ),
            or_(
                and_(current_launch_id.is_not(None), current_launch_id != TaskLaunchModel.id),
                current_launch_id.is_(None),
            ),
            TaskLaunchModel.status.in_([TaskLaunchStatus.FAILED, TaskLaunchStatus.SKIPPED, TaskLaunchStatus.FINISHED]),
        ),
        foreign_keys=[TaskLaunchModel.task_id],
        lazy="select",
        uselist=True,
        passive_deletes=True,
        order_by=lambda: desc(TaskLaunchModel.scheduled_at),
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("spec_id", "job_id", "id"),
        CheckConstraint(
            """
            CASE
                WHEN status = 'NEW'
                    THEN current_launch_id IS NULL AND latest_launch_id IS NULL
                WHEN status = 'PENDING'
                    THEN current_launch_id IS NOT NULL AND latest_launch_id IS NULL
                WHEN status = 'IN_PROGRESS'
                    THEN current_launch_id IS NOT NULL AND latest_launch_id IS NULL
                WHEN status = 'SUCCESS'
                    THEN current_launch_id IS NULL AND latest_launch_id IS NOT NULL
                WHEN status = 'FAILED'
                    THEN current_launch_id IS NULL AND latest_launch_id IS NOT NULL
                WHEN status = 'SKIPPED'
                    THEN current_launch_id IS NULL AND latest_launch_id IS NOT NULL
                ELSE false
            END
            """,
            name="scoped_tasks_status_check",
        ),
        {"extend_existing": True},
    )
