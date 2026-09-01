from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from packages.connectors.contracts import (
    ConnectorCapabilities,
    FetchPage,
    SourceEnvelope,
    SourceRecord,
    SyncMode,
)
from packages.connectors.sync import SynchronizationEngine, UnsupportedSyncModeError


@dataclass(slots=True)
class Adapter:
    pages: list[FetchPage]
    capabilities: ConnectorCapabilities = ConnectorCapabilities(
        provider="test_provider",
        connector_version="1.0.0",
        supported_source_types=("activity",),
        supports_polling=True,
        supports_backfill=True,
        supports_incremental_sync=True,
    )

    def fetch_page(
        self,
        *,
        connection_id: str,
        mode: SyncMode,
        cursor: str | None,
    ) -> FetchPage:
        del connection_id, mode, cursor
        return self.pages.pop(0)


@dataclass(slots=True)
class EvidenceSink:
    events: list[str]
    envelopes: list[SourceEnvelope] = field(default_factory=list)
    fail_after: int | None = None

    def persist(self, envelope: SourceEnvelope) -> None:
        if self.fail_after is not None and len(self.envelopes) >= self.fail_after:
            raise RuntimeError("simulated persistence failure")
        self.envelopes.append(envelope)
        self.events.append(f"persist:{envelope.record.source_record_id}")


@dataclass(slots=True)
class Checkpoints:
    events: list[str]
    committed: list[str] = field(default_factory=list)

    def commit(self, *, connection_id: str, cursor: str) -> None:
        del connection_id
        self.committed.append(cursor)
        self.events.append(f"checkpoint:{cursor}")


def _record(record_id: str) -> SourceRecord:
    return SourceRecord(
        source_record_type="activity",
        source_record_id=record_id,
        source_schema_version="1",
        payload_reference=f"object://test/{record_id}",
        payload_hash=f"hash-{record_id}",
    )


def test_checkpoint_advances_only_after_page_evidence_is_persisted() -> None:
    events: list[str] = []
    sink = EvidenceSink(events=events)
    checkpoints = Checkpoints(events=events)
    adapter = Adapter(
        pages=[
            FetchPage(records=(_record("a"), _record("b")), next_cursor="cursor-1", complete=False),
            FetchPage(records=(_record("c"),), next_cursor="cursor-2", complete=True),
        ]
    )

    result = SynchronizationEngine(evidence_sink=sink, checkpoint_store=checkpoints).run(
        adapter=adapter,
        connection_id="conn-1",
        mode=SyncMode.INCREMENTAL,
        correlation_id="corr-1",
    )

    assert events == [
        "persist:a",
        "persist:b",
        "checkpoint:cursor-1",
        "persist:c",
        "checkpoint:cursor-2",
    ]
    assert result.records_persisted == 3
    assert result.final_cursor == "cursor-2"


def test_persistence_failure_prevents_checkpoint_advance() -> None:
    events: list[str] = []
    sink = EvidenceSink(events=events, fail_after=1)
    checkpoints = Checkpoints(events=events)
    adapter = Adapter(
        pages=[FetchPage(records=(_record("a"), _record("b")), next_cursor="unsafe")]
    )

    with pytest.raises(RuntimeError, match="simulated persistence failure"):
        SynchronizationEngine(evidence_sink=sink, checkpoint_store=checkpoints).run(
            adapter=adapter,
            connection_id="conn-1",
            mode=SyncMode.INCREMENTAL,
        )

    assert checkpoints.committed == []
    assert events == ["persist:a"]


def test_undeclared_sync_capability_is_rejected() -> None:
    adapter = Adapter(
        pages=[],
        capabilities=ConnectorCapabilities(
            provider="test_provider",
            connector_version="1.0.0",
            supported_source_types=("activity",),
        ),
    )

    with pytest.raises(UnsupportedSyncModeError, match="incremental"):
        SynchronizationEngine(
            evidence_sink=EvidenceSink(events=[]),
            checkpoint_store=Checkpoints(events=[]),
        ).run(
            adapter=adapter,
            connection_id="conn-1",
            mode=SyncMode.INCREMENTAL,
        )
