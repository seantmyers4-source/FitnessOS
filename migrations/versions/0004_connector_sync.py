"""Add connector registry, connections, sync jobs, and checkpoints.

Revision ID: 0004_connector_sync
Revises: 0003_validation_runtime
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_connector_sync"
down_revision: str | None = "0003_validation_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connector_registration",
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("connector_version", sa.String(length=64), nullable=False),
        sa.Column("capability_manifest_reference", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("provider", "connector_version", name="uq_connector_registration"),
    )
    op.create_index("ix_connector_registration_provider", "connector_registration", ["provider"])

    op.create_table(
        "provider_connection",
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connector_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connector_registration.connector_id"),
            nullable=False,
        ),
        sa.Column(
            "athlete_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_entity.entity_id"),
            nullable=False,
        ),
        sa.Column("external_account_reference", sa.String(length=512), nullable=False),
        sa.Column("credential_reference", sa.String(length=1024), nullable=False),
        sa.Column("connection_state", sa.String(length=128), nullable=False),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True)),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_failed_sync_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_provider_connection_connector_id", "provider_connection", ["connector_id"])
    op.create_index(
        "ix_provider_connection_athlete_entity_id",
        "provider_connection",
        ["athlete_entity_id"],
    )
    op.create_index(
        "ix_provider_connection_connection_state",
        "provider_connection",
        ["connection_state"],
    )

    op.create_table(
        "sync_job",
        sa.Column("sync_job_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_connection.connection_id"),
            nullable=False,
        ),
        sa.Column("sync_mode", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_before", sa.String(length=2048)),
        sa.Column("checkpoint_after", sa.String(length=2048)),
        sa.Column("records_observed", sa.Integer(), nullable=False),
        sa.Column("records_persisted", sa.Integer(), nullable=False),
        sa.Column("records_failed", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sync_job_connection_id", "sync_job", ["connection_id"])
    op.create_index("ix_sync_job_status", "sync_job", ["status"])
    op.create_index("ix_sync_job_correlation_id", "sync_job", ["correlation_id"])

    op.create_table(
        "sync_checkpoint",
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("provider_connection.connection_id"),
            nullable=False,
        ),
        sa.Column("source_stream", sa.String(length=256), nullable=False),
        sa.Column("cursor_type", sa.String(length=128), nullable=False),
        sa.Column("cursor_value", sa.String(length=4096), nullable=False),
        sa.Column(
            "sync_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sync_job.sync_job_id"),
        ),
        sa.Column("provider_time", sa.DateTime(timezone=True)),
        sa.Column(
            "committed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "connection_id",
            "source_stream",
            name="uq_sync_checkpoint_stream",
        ),
    )
    op.create_index("ix_sync_checkpoint_connection_id", "sync_checkpoint", ["connection_id"])


def downgrade() -> None:
    op.drop_index("ix_sync_checkpoint_connection_id", table_name="sync_checkpoint")
    op.drop_table("sync_checkpoint")
    op.drop_index("ix_sync_job_correlation_id", table_name="sync_job")
    op.drop_index("ix_sync_job_status", table_name="sync_job")
    op.drop_index("ix_sync_job_connection_id", table_name="sync_job")
    op.drop_table("sync_job")
    op.drop_index("ix_provider_connection_connection_state", table_name="provider_connection")
    op.drop_index("ix_provider_connection_athlete_entity_id", table_name="provider_connection")
    op.drop_index("ix_provider_connection_connector_id", table_name="provider_connection")
    op.drop_table("provider_connection")
    op.drop_index("ix_connector_registration_provider", table_name="connector_registration")
    op.drop_table("connector_registration")
