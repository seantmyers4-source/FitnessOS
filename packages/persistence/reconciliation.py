from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.persistence.base import Base


class DuplicateEvaluation(Base):
    """Durable identity/duplicate evaluation record."""

    __tablename__ = "duplicate_evaluation"

    evaluation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    left_observation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    right_observation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String(256), nullable=False)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Float)
    evidence_reference: Mapped[str | None] = mapped_column(String(1024))
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReconciliationGroup(Base):
    """Groups multiple source observations around one provider-neutral entity candidate."""

    __tablename__ = "reconciliation_group"

    group_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    canonical_entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_entity.entity_id"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReconciliationMember(Base):
    """Observation membership in a reconciliation group."""

    __tablename__ = "reconciliation_member"
    __table_args__ = (UniqueConstraint("group_id", "observation_id", name="uq_reconciliation_member"),)

    member_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    group_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("reconciliation_group.group_id"),
        nullable=False,
        index=True,
    )
    observation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    relationship: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    decision_reference: Mapped[str | None] = mapped_column(String(1024))


class ReconciliationConflict(Base):
    """Explicit unresolved ambiguity/conflict; uncertainty never silently becomes a guess."""

    __tablename__ = "reconciliation_conflict"

    conflict_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    group_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reconciliation_group.group_id"), index=True
    )
    conflict_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    candidate_set_reference: Mapped[str | None] = mapped_column(String(1024))
    resolution_reference: Mapped[str | None] = mapped_column(String(1024))
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AuthorityDecision(Base):
    """Persisted result from an external CMAM-compatible authority resolver."""

    __tablename__ = "authority_decision"

    decision_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    canonical_entity_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_entity.entity_id"), index=True
    )
    metric_reference: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    selected_observation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    authority_version: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_reference: Mapped[str | None] = mapped_column(String(1024))
    decision: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reason_code: Mapped[str | None] = mapped_column(String(256))
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
