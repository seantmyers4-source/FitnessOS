"""Add reconciliation runtime persistence.

Revision ID: 0005_reconciliation
Revises: 0004_connector_sync
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_reconciliation"
down_revision: str | None = "0004_connector_sync"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "duplicate_evaluation",
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("left_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("right_observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_id", sa.String(length=256), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=128), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("evidence_reference", sa.String(length=1024)),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "reconciliation_group",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "canonical_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_entity.entity_id"),
        ),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "reconciliation_member",
        sa.Column("member_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reconciliation_group.group_id"),
            nullable=False,
        ),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("relationship", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("decision_reference", sa.String(length=1024)),
        sa.UniqueConstraint(
            "group_id", "observation_id", name="uq_reconciliation_member"
        ),
    )
    op.create_table(
        "reconciliation_conflict",
        sa.Column("conflict_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "group_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reconciliation_group.group_id"),
        ),
        sa.Column("conflict_type", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("candidate_set_reference", sa.String(length=1024)),
        sa.Column("resolution_reference", sa.String(length=1024)),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "authority_decision",
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "canonical_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_entity.entity_id"),
        ),
        sa.Column("metric_reference", sa.String(length=512), nullable=False),
        sa.Column("selected_observation_id", postgresql.UUID(as_uuid=True)),
        sa.Column("authority_version", sa.String(length=128), nullable=False),
        sa.Column("rule_reference", sa.String(length=1024)),
        sa.Column("decision", sa.String(length=128), nullable=False),
        sa.Column("reason_code", sa.String(length=256)),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("authority_decision")
    op.drop_table("reconciliation_conflict")
    op.drop_table("reconciliation_member")
    op.drop_table("reconciliation_group")
    op.drop_table("duplicate_evaluation")
