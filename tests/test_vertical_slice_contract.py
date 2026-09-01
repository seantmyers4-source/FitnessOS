from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from packages.connectors.contracts import DeliveryMethod, SourceEnvelope, SourceRecord
from packages.contracts.reconciliation import AuthorityCandidate, ReconciliationObservation
from packages.contracts.vertical_slice import CanonicalCommitRequest


def test_vertical_slice_contract_keeps_provider_id_out_of_canonical_identity() -> None:
    record = SourceRecord(
        source_record_type="completed_activity",
        source_record_id="provider-activity-123",
        source_schema_version="test-v1",
        payload_reference="evidence://provider-activity-123",
        payload_hash="abc123",
        observed_at=datetime.now(UTC),
    )
    envelope = SourceEnvelope(
        provider="garmin",
        connector_version="integration-owned",
        connection_id="connection-1",
        delivery_method=DeliveryMethod.POLL,
        correlation_id="correlation-1",
        record=record,
    )
    observation_id = uuid4()
    observation = ReconciliationObservation(
        observation_id=observation_id,
        entity_type="activity",
        source="garmin",
        external_identity="provider-activity-123",
    )
    candidate = AuthorityCandidate(
        observation_id=observation_id,
        metric_reference="distance",
        source="garmin",
        value_reference="observation://distance",
    )

    request = CanonicalCommitRequest(
        entity_type="activity",
        canonical_entity_id=None,
        source_envelope=envelope,
        normalized_observation=observation,
        authority_candidates=(candidate,),
        metric_reference="distance",
        effective_from=datetime.now(UTC),
        quality_state="test-only",
        provenance_reference="provenance://test",
    )

    assert request.canonical_entity_id is None
    assert request.source_envelope.record.source_record_id == "provider-activity-123"
    assert request.normalized_observation.observation_id == observation_id
