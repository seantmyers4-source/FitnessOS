"""Add durable validation pipeline, quarantine, and replay records.

Revision ID: 0003_validation_runtime
Revises: 0002_apdw_history
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_validation_runtime"
down_revision: str | None = "0002_apdw_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_execution",
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_evidence.evidence_id"),
            nullable=False,
        ),
        sa.Column("pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("failure_stage", sa.String(length=128)),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_pipeline_execution_evidence_id", "pipeline_execution", ["evidence_id"])
    op.create_index("ix_pipeline_execution_status", "pipeline_execution", ["status"])
    op.create_index(
        "ix_pipeline_execution_correlation_id",
        "pipeline_execution",
        ["correlation_id"],
    )

    op.create_table(
        "pipeline_stage_execution",
        sa.Column("stage_execution_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "execution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_execution.execution_id"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=128), nullable=False),
        sa.Column("stage_order", sa.Integer(), nullable=False),
        sa.Column("processor_version", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=128), nullable=False),
        sa.Column("rule_reference", sa.String(length=512)),
        sa.Column("details_reference", sa.String(length=1024)),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("execution_id", "stage_order", name="uq_pipeline_stage_order"),
    )
    op.create_index(
        "ix_pipeline_stage_execution_execution_id",
        "pipeline_stage_execution",
        ["execution_id"],
    )

    op.create_table(
        "quarantine_record",
        sa.Column("quarantine_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_evidence.evidence_id"),
            nullable=False,
        ),
        sa.Column(
            "execution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_execution.execution_id"),
            nullable=False,
        ),
        sa.Column("failure_stage", sa.String(length=128), nullable=False),
        sa.Column("rule_reference", sa.String(length=512)),
        sa.Column("resolution_state", sa.String(length=128), nullable=False),
        sa.Column("resolution_reference", sa.String(length=1024)),
        sa.Column(
            "quarantined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("released_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_quarantine_record_evidence_id", "quarantine_record", ["evidence_id"])
    op.create_index("ix_quarantine_record_execution_id", "quarantine_record", ["execution_id"])
    op.create_index(
        "ix_quarantine_record_resolution_state",
        "quarantine_record",
        ["resolution_state"],
    )

    op.create_table(
        "replay_request",
        sa.Column("replay_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_evidence.evidence_id"),
            nullable=False,
        ),
        sa.Column(
            "prior_execution_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_execution.execution_id"),
        ),
        sa.Column("reason", sa.String(length=512), nullable=False),
        sa.Column("requested_pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("requested_by", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=128), nullable=False),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_replay_request_evidence_id", "replay_request", ["evidence_id"])
    op.create_index("ix_replay_request_status", "replay_request", ["status"])


def downgrade() -> None:
    op.drop_index("ix_replay_request_status", table_name="replay_request")
    op.drop_index("ix_replay_request_evidence_id", table_name="replay_request")
    op.drop_table("replay_request")
    op.drop_index("ix_quarantine_record_resolution_state", table_name="quarantine_record")
    op.drop_index("ix_quarantine_record_execution_id", table_name="quarantine_record")
    op.drop_index("ix_quarantine_record_evidence_id", table_name="quarantine_record")
    op.drop_table("quarantine_record")
    op.drop_index(
        "ix_pipeline_stage_execution_execution_id",
        table_name="pipeline_stage_execution",
    )
    op.drop_table("pipeline_stage_execution")
    op.drop_index("ix_pipeline_execution_correlation_id", table_name="pipeline_execution")
    op.drop_index("ix_pipeline_execution_status", table_name="pipeline_execution")
    op.drop_index("ix_pipeline_execution_evidence_id", table_name="pipeline_execution")
    op.drop_table("pipeline_execution")
