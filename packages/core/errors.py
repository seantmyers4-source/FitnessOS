from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class ErrorClass(StrEnum):
    VALIDATION = "VALIDATION"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    DEPENDENCY = "DEPENDENCY"
    RATE_LIMIT = "RATE_LIMIT"
    TIMEOUT = "TIMEOUT"
    PERSISTENCE = "PERSISTENCE"
    MIGRATION = "MIGRATION"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True, slots=True)
class FitnessOSError(Exception):
    error_code: str
    error_class: ErrorClass
    service: str
    operation: str
    correlation_id: str
    retryable: bool
    safe_message: str
    details_reference: str | None = None

    @property
    def timestamp(self) -> datetime:
        return datetime.now(UTC)
