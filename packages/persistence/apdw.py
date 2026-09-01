from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.persistence.base import Base


class SourceEvidence(Base):
    """Immutable reference to evidence received from a source system."""

    __tablename__ = "source_evidence"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "source_record_type",
            "source_record_id",
            "payload_hash",
            name="uq_source_evidence_fingerprint",
        ),
    )

    evidence_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(512), nullable=False)
    source_schema_version: Mapped[str | None] = mapped_column(String(128))
    payload_reference: Mapped[str] = mapped_column(String(1024), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)


class CanonicalEntity(Base):
    """Provider-independent identity container without domain semantics."""

    __tablename__ = "canonical_entity"

    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ExternalIdentity(Base):
    """Maps a source-system identifier to a stable FitnessOS entity identity."""

    __tablename__ = "external_identity"
    __table_args__ = (
        UniqueConstraint(
            "provider", "external_entity_type", "external_identifier", name="uq_external_identity"
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name="ck_external_identity_valid_range"
        ),
    )

    external_identity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_entity.entity_id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(128), nullable=False)
    external_entity_type: Mapped[str] = mapped_column(String(128), nullable=False)
    external_identifier: Mapped[str] = mapped_column(String(512), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CanonicalVersion(Base):
    """Non-destructive canonical version with effective and system time support."""

    __tablename__ = "canonical_version"
    __table_args__ = (
        UniqueConstraint("entity_id", "version_number", name="uq_canonical_entity_version"),
        CheckConstraint("version_number > 0", name="ck_canonical_version_positive"),
        CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_canonical_version_effective_range",
        ),
        CheckConstraint(
            "system_to IS NULL OR system_to > system_from",
            name="ck_canonical_version_system_range",
        ),
    )

    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_entity.entity_id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    system_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    system_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_version.version_id")
    )


class ProvenanceLink(Base):
    """Many-to-many lineage between canonical versions and source evidence."""

    __tablename__ = "provenance_link"
    __table_args__ = (
        UniqueConstraint(
            "version_id", "evidence_id", "relationship_type", name="uq_provenance_link"
        ),
    )

    provenance_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_version.version_id"), nullable=False, index=True
    )
    evidence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("source_evidence.evidence_id"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(128), nullable=False)
    transformation_reference: Mapped[str | None] = mapped_column(String(512))
    authority_decision_reference: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class QualityAssessment(Base):
    """Persisted quality metadata using externally governed state values."""

    __tablename__ = "quality_assessment"

    quality_assessment_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    subject_type: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    quality_state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    rule_reference: Mapped[str | None] = mapped_column(String(512))
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    details_reference: Mapped[str | None] = mapped_column(String(1024))


class CurrentProjection(Base):
    """Disposable pointer from a projection to the current canonical version."""

    __tablename__ = "current_projection"
    __table_args__ = (
        UniqueConstraint("projection_type", "entity_id", name="uq_current_projection"),
    )

    projection_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    projection_type: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_entity.entity_id"), nullable=False, index=True
    )
    current_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_version.version_id"), nullable=False
    )
    projection_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    projected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class IdempotencyRecord(Base):
    """Records one logical mutation for a scoped idempotency key."""

    __tablename__ = "idempotency_record"
    __table_args__ = (
        UniqueConstraint(
            "operation_scope", "idempotency_key", "operation_version", name="uq_idempotency_key"
        ),
    )

    operation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    operation_scope: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(512), nullable=False)
    operation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    result_reference: Mapped[str | None] = mapped_column(String(1024))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EventOutbox(Base):
    """Durable post-commit publication record for canonical events."""

    __tablename__ = "event_outbox"

    outbox_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True)
    aggregate_type: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(256), nullable=False)
    event_version: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    causation_id: Mapped[str | None] = mapped_column(String(128))
    publication_state: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
