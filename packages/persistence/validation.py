from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.persistence.base import Base


class PipelineExecution(Base):
    """Durable record of one processing attempt against immutable evidence."""

    __tablename__ = "pipeline_execution"

    execution_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    evidence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("source_evidence.evidence_id"), nullable=False, index=True
    )
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_stage: Mapped[str | None] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PipelineStageExecution(Base):
    """Auditable execution record for one required pipeline layer."""

    __tablename__ = "pipeline_stage_execution"
    __table_args__ = (
        UniqueConstraint("execution_id", "stage_order", name="uq_pipeline_stage_order"),
    )

    stage_execution_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    execution_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pipeline_execution.execution_id"), nullable=False, index=True
    )
    stage: Mapped[str] = mapped_column(String(128), nullable=False)
    stage_order: Mapped[int] = mapped_column(Integer, nullable=False)
    processor_version: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_reference: Mapped[str | None] = mapped_column(String(512))
    details_reference: Mapped[str | None] = mapped_column(String(1024))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuarantineRecord(Base):
    """Recoverable holding record for evidence that cannot continue processing."""

    __tablename__ = "quarantine_record"

    quarantine_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    evidence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("source_evidence.evidence_id"), nullable=False, index=True
    )
    execution_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pipeline_execution.execution_id"), nullable=False, index=True
    )
    failure_stage: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_reference: Mapped[str | None] = mapped_column(String(512))
    resolution_state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resolution_reference: Mapped[str | None] = mapped_column(String(1024))
    quarantined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReplayRequest(Base):
    """Records a new processing attempt requested from preserved source evidence."""

    __tablename__ = "replay_request"

    replay_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    evidence_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("source_evidence.evidence_id"), nullable=False, index=True
    )
    prior_execution_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("pipeline_execution.execution_id")
    )
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    requested_pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
