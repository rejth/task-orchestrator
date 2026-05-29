from __future__ import annotations

import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.journal import LogFileExtension, LogLevel, LogType
from src.infrastructure.database.base import Base


class LogFileModel(Base):
    __tablename__ = "log_files"

    log_id: Mapped[UUID] = mapped_column(ForeignKey("journal.id", ondelete="CASCADE"), primary_key=True)
    filename: Mapped[str]
    extension: Mapped[LogFileExtension]
    data: Mapped[bytes]

    __table_args__ = ({"extend_existing": True},)


class ExecutionLogRecordModel(Base):
    __tablename__ = "journal"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    message: Mapped[str]
    launch_id: Mapped[UUID] = mapped_column(ForeignKey("task_launches.id", ondelete="CASCADE"), index=True)
    timestamp: Mapped[datetime.datetime]
    level: Mapped[LogLevel] = mapped_column(index=True)
    type: Mapped[LogType] = mapped_column(index=True)

    file: Mapped[Optional[LogFileModel]] = relationship(LogFileModel, passive_deletes=True, uselist=False)

    __table_args__ = ({"extend_existing": True},)
