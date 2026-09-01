from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from packages.connectors.contracts import SourceEnvelope, SyncMode
from packages.connectors.garmin import (
    GarminActivityPage,
    GarminClientError,
    GarminCompletedActivityAdapter,
)
from packages.connectors.sync import SynchronizationEngine
from packages.contracts.reconciliation import AuthorityCandidate, AuthorityResolution, ReconciliationObservation
from packages.reconciliation.runtime import ReconciliationEngine, deterministic_external_identity_strategy
from packages.validation.contracts import PipelineContext, StageResult, ValidationLayer
from packages.validation.engine import ValidationPipeline


class EvidenceStore:
    def __init__(self) -> None:
        self.raw_payloads: dict[str, bytes] = {}
        self.envelopes: list[SourceEnvelope] = []

    def persist_payload(self, *, connection_id: str, source_record_id: str, payload: bytes, payload_hash: str) -> str:
        reference = f"evidence://garmin/{connection_id}/{source_record_id}/{payload_hash}"
        self.raw_payloads[reference] = payload
        return reference

    def persist(self, envelope: SourceEnvelope) -> None:
        self.envelopes.append(envelope)


class Checkpoints:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.cursors: list[str] = []

    def commit(self, *, connection_id: str, cursor: str) -> None:
        if self.fail:
            raise RuntimeError("checkpoint unavailable")
        self.cursors.append(cursor)


class Client:
    def __init__(self, pages: dict[str | None, GarminActivityPage]) -> None:
        self.pages = pages

    def fetch_completed_activities(self, *, connection_id: str, cursor: str | None, backfill: bool) -> GarminActivityPage:
        return self.pages[cursor]


@dataclass
class Processor:
    layer: ValidationLayer
    outcome: str = "PASS"
    continue_processing: bool = True
    derived_payload: dict[str, object] | None = None
    processor_version: str = "cert-v1"

    def process(self, context: PipelineContext) -> StageResult:
        return StageResult(
            outcome=self.outcome,
            continue_processing=self.continue_processing,
            derived_payload=self.derived_payload,
        )


def activity() -> dict[str, object]:
    return {
        "activityId": "G-CERT-1",
        "activityType": "RUNNING",
        "startTimeInSeconds": 1788200000,
        "durationInSeconds": 3600,
        "distanceInMeters": 10000.0,
        "averageHeartRateInBeatsPerMinute": 148,
    }


def pipeline(*, stop_at_schema: bool = False) -> ValidationPipeline:
    processors = [
        Processor(ValidationLayer.TRANSPORT_INTEGRITY),
        Processor(ValidationLayer.SCHEMA, outcome="QUARANTINE", continue_processing=False)
        if stop_at_schema
        else Processor(ValidationLayer.SCHEMA),
        Processor(ValidationLayer.NORMALIZATION, derived_payload={"distance_meters_candidate": 10000.0}),
        Processor(ValidationLayer.SEMANTIC_PLAUSIBILITY),
        Processor(ValidationLayer.AUTHORITY_RECONCILIATION),
        Processor(ValidationLayer.CONSEQUENTIAL_USE),
    ]
    return ValidationPipeline(processors)


def test_integrated_garmin_path_reaches_shared_validation_and_authority_boundary() -> None:
    store = EvidenceStore()
    checkpoints = Checkpoints()
    adapter = GarminCompletedActivityAdapter(
        client=Client({None: GarminActivityPage((activity(),), next_cursor="c1", complete=True)}),
        evidence_store=store,
    )
    sync = SynchronizationEngine(evidence_sink=store, checkpoint_store=checkpoints)

    result = sync.run(adapter=adapter, connection_id="athlete-connection", mode=SyncMode.INCREMENTAL)

    assert result.records_persisted == 1
    assert checkpoints.cursors == ["c1"]
    envelope = store.envelopes[0]
    raw_before = store.raw_payloads[envelope.record.payload_reference]

    validation = pipeline().run(
        PipelineContext(
            evidence_id=uuid4(),
            correlation_id=envelope.correlation_id,
            source_payload_reference=envelope.record.payload_reference,
            source_metadata={"provider": envelope.provider, "source_record_id": envelope.record.source_record_id},
        )
    )
    assert validation.completed
    assert len(validation.stages) == 6
    assert store.raw_payloads[envelope.record.payload_reference] == raw_before
    assert validation.final_context.derived_payload["distance_meters_candidate"] == 10000.0

    observation_id = uuid4()
    observation = ReconciliationObservation(observation_id, "activity", "garmin", envelope.record.source_record_id)
    strategy = deterministic_external_identity_strategy(strategy_id="exact_external_identity", strategy_version="1")
    reconciliation = ReconciliationEngine(duplicate_strategy=strategy)
    candidate = AuthorityCandidate(observation_id, "distance", "garmin", "observation://distance")
    authority = reconciliation.resolve_authority(
        entity_type="activity", metric_reference="distance", candidates=(candidate,)
    )
    assert authority.decision == "UNRESOLVED"
    assert authority.selected_observation_id is None
    assert envelope.record.source_record_id == "G-CERT-1"


def test_external_authority_controls_selection_without_garmin_precedence() -> None:
    selected = uuid4()

    class Resolver:
        def resolve(self, *, entity_type: str, metric_reference: str, candidates: tuple[AuthorityCandidate, ...]) -> AuthorityResolution:
            return AuthorityResolution(selected, "CMAM-cert", "rule://distance", "RESOLVED")

    strategy = deterministic_external_identity_strategy(strategy_id="exact_external_identity", strategy_version="1")
    engine = ReconciliationEngine(duplicate_strategy=strategy, authority_resolver=Resolver())
    candidate = AuthorityCandidate(selected, "distance", "synthetic-authorized-source", "observation://distance")
    resolution = engine.resolve_authority(entity_type="activity", metric_reference="distance", candidates=(candidate,))

    assert resolution.decision == "RESOLVED"
    assert resolution.selected_observation_id == selected
    assert resolution.authority_version == "CMAM-cert"


def test_checkpoint_failure_preserves_evidence_and_retry_replays_safely() -> None:
    store = EvidenceStore()
    adapter = GarminCompletedActivityAdapter(
        client=Client({None: GarminActivityPage((activity(),), next_cursor="c1", complete=True)}),
        evidence_store=store,
    )

    with pytest.raises(RuntimeError, match="checkpoint unavailable"):
        SynchronizationEngine(evidence_sink=store, checkpoint_store=Checkpoints(fail=True)).run(
            adapter=adapter, connection_id="athlete-connection", mode=SyncMode.INCREMENTAL
        )

    assert len(store.envelopes) == 1
    first_hash = store.envelopes[0].record.payload_hash

    checkpoints = Checkpoints()
    SynchronizationEngine(evidence_sink=store, checkpoint_store=checkpoints).run(
        adapter=adapter, connection_id="athlete-connection", mode=SyncMode.INCREMENTAL
    )
    assert len(store.envelopes) == 2
    assert store.envelopes[1].record.payload_hash == first_hash
    assert checkpoints.cursors == ["c1"]


def test_pipeline_failure_stops_before_downstream_canonical_decision() -> None:
    result = pipeline(stop_at_schema=True).run(
        PipelineContext(
            evidence_id=uuid4(),
            correlation_id="cert-failure",
            source_payload_reference="evidence://garmin/failure",
        )
    )

    assert not result.completed
    assert len(result.stages) == 2
    assert result.stages[-1].layer is ValidationLayer.SCHEMA
    assert result.stages[-1].outcome == "QUARANTINE"
