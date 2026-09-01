from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

_correlation_id: ContextVar[str | None] = ContextVar("fitnessos_correlation_id", default=None)


def new_correlation_id() -> str:
    value = str(uuid4())
    _correlation_id.set(value)
    return value


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str:
    return _correlation_id.get() or new_correlation_id()
