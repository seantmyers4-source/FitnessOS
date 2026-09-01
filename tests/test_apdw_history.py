from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from packages.persistence.apdw import (
    CanonicalEntity,
    CanonicalVersion,
    CurrentProjection,
    EventOutbox,
    IdempotencyRecord,
    ProvenanceLink,
    QualityAssessment,
    SourceEvidence,
)

DATABASE_URL = os.environ.get(
    "FITNESSOS_DATABASE_URL",
    "postgresql+psycopg://fitnessos:fitnessos@localhost:5432/fitnessos",
)


def test_history_lineage_projection_and_outbox_are_non_destructive() -> None:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        entity = CanonicalEntity(entity_type="test_entity")
        evidence = SourceEvidence(
            provider="test_provider",
            source_record_type="test_record",
            source_record_id="record-001",
            payload_reference="object://test/record-001-v1",
            payload_hash="hash-v1",
            correlation_id="corr-001",
        )
        session.add_all([entity, evidence])
        session.flush()

        effective = datetime(2026, 8, 31, 12, tzinfo=UTC)
        v1 = CanonicalVersion(
            entity_id=entity.entity_id,
            version_number=1,
            effective_from=effective,
            payload={"test_value": 1},
            correlation_id="corr-001",
        )
        session.add(v1)
        session.flush()

        session.add(
            ProvenanceLink(
                version_id=v1.version_id,
                evidence_id=evidence.evidence_id,
                relationship_type="source_evidence",
            )
        )
        session.add(
            QualityAssessment(
                subject_type="canonical_version",
                subject_id=v1.version_id,
                quality_state="test_state",
            )
        )
        session.flush()

        v1.system_to = datetime.now(UTC)
        v2 = CanonicalVersion(
            entity_id=entity.entity_id,
            version_number=2,
            effective_from=effective,
            payload={"test_value": 2},
            correlation_id="corr-002",
            supersedes_version_id=v1.version_id,
        )
        session.add(v2)
        session.flush()

        projection = CurrentProjection(
            projection_type="test_projection",
            entity_id=entity.entity_id,
            current_version_id=v2.version_id,
            projection_version=1,
        )
        event_id = uuid4()
        outbox = EventOutbox(
            event_id=event_id,
            aggregate_type="test_entity",
            aggregate_id=entity.entity_id,
            aggregate_version=2,
            event_type="test.updated",
            event_version="1.0.0",
            payload={"version_id": str(v2.version_id)},
            correlation_id="corr-002",
            publication_state="pending",
            attempt_count=0,
        )
        session.add_all([projection, outbox])
        session.flush()

        versions = session.scalars(
            select(CanonicalVersion)
            .where(CanonicalVersion.entity_id == entity.entity_id)
            .order_by(CanonicalVersion.version_number)
        ).all()
        current = session.scalar(
            select(CurrentProjection).where(CurrentProjection.entity_id == entity.entity_id)
        )

        assert [version.version_number for version in versions] == [1, 2]
        assert versions[0].payload == {"test_value": 1}
        assert versions[0].system_to is not None
        assert versions[1].supersedes_version_id == versions[0].version_id
        assert current is not None
        assert current.current_version_id == versions[1].version_id
        assert outbox.event_id == event_id
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def test_source_evidence_allows_changed_payload_without_reusing_identity() -> None:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        first = SourceEvidence(
            provider="test_provider",
            source_record_type="activity",
            source_record_id="same-source-id",
            payload_reference="object://test/v1",
            payload_hash="hash-one",
            correlation_id="corr-one",
        )
        second = SourceEvidence(
            provider="test_provider",
            source_record_type="activity",
            source_record_id="same-source-id",
            payload_reference="object://test/v2",
            payload_hash="hash-two",
            correlation_id="corr-two",
            observed_at=datetime.now(UTC) + timedelta(seconds=1),
        )
        session.add_all([first, second])
        session.flush()

        assert first.evidence_id != second.evidence_id
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


def test_idempotency_scope_has_one_logical_key() -> None:
    record = IdempotencyRecord(
        operation_scope="test_scope",
        idempotency_key="key-001",
        operation_version="1",
        input_hash="hash-001",
        status="started",
    )

    assert record.operation_scope == "test_scope"
    assert record.idempotency_key == "key-001"
    assert record.input_hash == "hash-001"
