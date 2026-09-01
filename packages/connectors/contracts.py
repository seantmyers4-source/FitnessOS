from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class DeliveryMethod(StrEnum):
    WEBHOOK = "webhook"
    POLL = "poll"
    BACKFILL = "backfill"
    REPLAY = "replay"
    IMPORT = "import"


class SyncMode(StrEnum):
    INCREMENTAL = "incremental"
    BACKFILL = "backfill"
    WEBHOOK_PROCESSING = "webhook_processing"
    REPLAY = "replay"


@dataclass(frozen=True, slots=True)
class ConnectorCapabilities:
    provider: str
    connector_version: str
    supported_source_types: tuple[str, ...]
    supports_webhooks: bool = False
    supports_polling: bool = False
    supports_backfill: bool = False
    supports_incremental_sync: bool = False
    supports_deletions: bool = False
    supports_auth_refresh: bool = False
    checkpoint_strategy: str = "opaque_cursor"


@dataclass(frozen=True, slots=True)
class SourceRecord:
    source_record_type: str
    source_record_id: str
    source_schema_version: str | None
    payload_reference: str
    payload_hash: str
    observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class SourceEnvelope:
    provider: str
    connector_version: str
    connection_id: str
    delivery_method: DeliveryMethod
    correlation_id: str
    record: SourceRecord
    checkpoint_reference: str | None = None
    received_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FetchPage:
    records: tuple[SourceRecord, ...] = field(default_factory=tuple)
    next_cursor: str | None = None
    complete: bool = True


class ProviderAdapter(Protocol):
    @property
    def capabilities(self) -> ConnectorCapabilities: ...

    def fetch_page(
        self,
        *,
        connection_id: str,
        mode: SyncMode,
        cursor: str | None,
    ) -> FetchPage: ...


class EvidenceSink(Protocol):
    def persist(self, envelope: SourceEnvelope) -> None: ...


class CheckpointStore(Protocol):
    def commit(self, *, connection_id: str, cursor: str) -> None: ...
