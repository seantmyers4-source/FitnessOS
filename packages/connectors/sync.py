from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from packages.connectors.contracts import (
    CheckpointStore,
    DeliveryMethod,
    EvidenceSink,
    ProviderAdapter,
    SourceEnvelope,
    SyncMode,
)


class UnsupportedSyncModeError(ValueError):
    """Raised when shared infrastructure is asked to use an undeclared capability."""


@dataclass(frozen=True, slots=True)
class SyncResult:
    correlation_id: str
    records_persisted: int
    final_cursor: str | None
    complete: bool


class SynchronizationEngine:
    """Provider-neutral synchronization with persistence-before-checkpoint ordering."""

    def __init__(self, *, evidence_sink: EvidenceSink, checkpoint_store: CheckpointStore) -> None:
        self._evidence_sink = evidence_sink
        self._checkpoint_store = checkpoint_store

    def run(
        self,
        *,
        adapter: ProviderAdapter,
        connection_id: str,
        mode: SyncMode,
        initial_cursor: str | None = None,
        correlation_id: str | None = None,
    ) -> SyncResult:
        self._validate_capability(adapter, mode)
        correlation = correlation_id or str(uuid4())
        cursor = initial_cursor
        persisted = 0

        while True:
            page = adapter.fetch_page(connection_id=connection_id, mode=mode, cursor=cursor)
            delivery_method = _delivery_method(mode)

            for record in page.records:
                envelope = SourceEnvelope(
                    provider=adapter.capabilities.provider,
                    connector_version=adapter.capabilities.connector_version,
                    connection_id=connection_id,
                    delivery_method=delivery_method,
                    correlation_id=correlation,
                    record=record,
                    checkpoint_reference=cursor,
                )
                self._evidence_sink.persist(envelope)
                persisted += 1

            if page.next_cursor is not None:
                self._checkpoint_store.commit(
                    connection_id=connection_id,
                    cursor=page.next_cursor,
                )
                cursor = page.next_cursor

            if page.complete:
                return SyncResult(
                    correlation_id=correlation,
                    records_persisted=persisted,
                    final_cursor=cursor,
                    complete=True,
                )

            if page.next_cursor is None:
                raise RuntimeError("incomplete provider page did not supply a resume cursor")

    @staticmethod
    def _validate_capability(adapter: ProviderAdapter, mode: SyncMode) -> None:
        capabilities = adapter.capabilities
        supported = {
            SyncMode.INCREMENTAL: capabilities.supports_incremental_sync,
            SyncMode.BACKFILL: capabilities.supports_backfill,
            SyncMode.WEBHOOK_PROCESSING: capabilities.supports_webhooks,
            SyncMode.REPLAY: True,
        }
        if not supported[mode]:
            raise UnsupportedSyncModeError(
                f"{capabilities.provider} does not declare support for {mode.value}"
            )


def _delivery_method(mode: SyncMode) -> DeliveryMethod:
    return {
        SyncMode.INCREMENTAL: DeliveryMethod.POLL,
        SyncMode.BACKFILL: DeliveryMethod.BACKFILL,
        SyncMode.WEBHOOK_PROCESSING: DeliveryMethod.WEBHOOK,
        SyncMode.REPLAY: DeliveryMethod.REPLAY,
    }[mode]
