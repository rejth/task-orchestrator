from __future__ import annotations

import datetime
from abc import ABCMeta
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from uuid import UUID


class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogType(Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    FILE = "FILE"


class LogFileExtension(Enum):
    TSV = "TSV"
    JSON = "JSON"


@dataclass
class BaseLogRecord(metaclass=ABCMeta):
    level: LogLevel
    message: str
    timestamp: datetime.datetime

    def __str__(self) -> str:
        return self.message


@dataclass
class UnclassifiedLogRecord(BaseLogRecord):
    @property
    def type(self) -> LogType:
        return LogType.UNCLASSIFIED


@dataclass
class FileLogRecord(BaseLogRecord):
    filename: str
    extension: LogFileExtension
    data: bytes

    @property
    def type(self) -> LogType:
        return LogType.FILE

    @property
    def full_filename(self) -> str:
        match self.extension:
            case LogFileExtension.TSV:
                return f"{self.filename}.tsv"
            case LogFileExtension.JSON:
                return f"{self.filename}.json"

    @property
    def mimetype(self) -> str:
        match self.extension:
            case LogFileExtension.TSV:
                return "text/csv"
            case LogFileExtension.JSON:
                return "application/json"

    @property
    def file_wrapper(self) -> StringIO:
        return StringIO(self.data.decode())


@dataclass
class LaunchLogRecord:
    id: UUID
    launch_id: UUID
    log: Log


Log = UnclassifiedLogRecord | FileLogRecord
