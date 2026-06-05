import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, asc
from sqlalchemy.orm import Mapped, mapped_column, relationship

from task_orchestrator.domain.launch import TaskLaunchStatus
from task_orchestrator.infrastructure.database.base import Base
from task_orchestrator.infrastructure.database.models.journal import ExecutionLogRecordModel


class TaskLaunchModel(Base):
    __tablename__ = "task_launches"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("scoped_tasks.id", ondelete="CASCADE"), index=True)
    message: Mapped[str]
    status: Mapped[TaskLaunchStatus] = mapped_column(index=True)

    scheduled_at: Mapped[datetime.datetime]
    scheduled_by: Mapped[str]

    started_at: Mapped[Optional[datetime.datetime]]
    finished_at: Mapped[Optional[datetime.datetime]]
    failed_at: Mapped[Optional[datetime.datetime]]
    is_aborted: Mapped[Optional[bool]]
    skipped_at: Mapped[Optional[datetime.datetime]]

    journal: Mapped[list[ExecutionLogRecordModel]] = relationship(
        ExecutionLogRecordModel,
        lazy="select",
        order_by=lambda: asc(ExecutionLogRecordModel.timestamp),
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            """
            CASE
                WHEN status = 'PENDING'
                    THEN started_at IS NULL AND finished_at IS NULL AND failed_at IS NULL
                    AND is_aborted IS NULL AND skipped_at IS NULL
                WHEN status = 'IN_PROGRESS'
                    THEN started_at IS NOT NULL AND finished_at IS NULL AND failed_at IS NULL
                    AND is_aborted IS NULL AND skipped_at IS NULL
                WHEN status = 'FINISHED'
                    THEN started_at IS NOT NULL AND finished_at IS NOT NULL AND failed_at IS NULL
                    AND is_aborted IS NULL AND skipped_at IS NULL
                WHEN status = 'FAILED'
                    THEN started_at IS NOT NULL AND finished_at IS NULL AND failed_at IS NOT NULL
                    AND is_aborted IS NOT NULL AND skipped_at IS NULL
                WHEN status = 'SKIPPED'
                    THEN started_at IS NOT NULL AND finished_at IS NULL AND failed_at IS NULL
                    AND is_aborted IS NULL AND skipped_at IS NOT NULL
                ELSE false
            END
            """,
            name="task_launches_status_check",
        ),
        {"extend_existing": True},
    )
