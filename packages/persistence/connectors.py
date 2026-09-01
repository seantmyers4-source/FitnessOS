from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.persistence.base import Base


class ConnectorRegistration(Base):
    """Provider-neutral registration for a versioned connector implementation."""

    __tablename__ = "connector_registration"
    __table_args__ = (
        UniqueConstraint("provider", "connector_version", name="uq_connector_registration"),
    )

    connector_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    provider: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    connector_version: Mapped[str] = mapped_column(String(64), nullable=False)
    capability_manifest_reference: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProviderConnection(Base):
    """Connection metadata with a secret reference rather than stored provider credentials."""

    __tablename__ = "provider_connection"

    connection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    connector_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("connector_registration.connector_id"),
        nullable=False,
        index=True,
    )
    athlete_entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("canonical_entity.entity_id"), nullable=False, index=True
    )
    external_account_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    credential_reference: Mapped[str] = mapped_column(String(1024), nullable=False)
    connection_state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncJob(Base):
    """Durable synchronization execution metadata."""

    __tablename__ = "sync_job"

    sync_job_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    connection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("provider_connection.connection_id"),
        nullable=False,
        index=True,
    )
    sync_mode: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    checkpoint_before: Mapped[str | None] = mapped_column(String(2048))
    checkpoint_after: Mapped[str | None] = mapped_column(String(2048))
    records_observed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_persisted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncCheckpoint(Base):
    """Durable resume cursor committed only after the required evidence boundary."""

    __tablename__ = "sync_checkpoint"
    __table_args__ = (
        UniqueConstraint("connection_id", "source_stream", name="uq_sync_checkpoint_stream"),
    )

    checkpoint_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    connection_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("provider_connection.connection_id"),
        nullable=False,
        index=True,
    )
    source_stream: Mapped[str] = mapped_column(String(256), nullable=False)
    cursor_type: Mapped[str] = mapped_column(String(128), nullable=False)
    cursor_value: Mapped[str] = mapped_column(String(4096), nullable=False)
    sync_job_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sync_job.sync_job_id")
    )
    provider_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
