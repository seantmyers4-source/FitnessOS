"""Add APDW identity, history, lineage, projection, idempotency, and outbox primitives.

Revision ID: 0002_apdw_history
Revises: 0001_platform_foundation
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_apdw_history"
down_revision: str | None = "0001_platform_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_evidence",
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("source_record_type", sa.String(length=128), nullable=False),
        sa.Column("source_record_id", sa.String(length=512), nullable=False),
        sa.Column("source_schema_version", sa.String(length=128)),
        sa.Column("payload_reference", sa.String(length=1024), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.UniqueConstraint(
            "provider",
            "source_record_type",
            "source_record_id",
            "payload_hash",
            name="uq_source_evidence_fingerprint",
        ),
    )

    op.create_table(
        "canonical_entity",
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_canonical_entity_entity_type", "canonical_entity", ["entity_type"])

    op.create_table(
        "external_identity",
        sa.Column("external_identity_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_entity.entity_id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=128), nullable=False),
        sa.Column("external_entity_type", sa.String(length=128), nullable=False),
        sa.Column("external_identifier", sa.String(length=512), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column(
            "first_observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name="ck_external_identity_valid_range"
        ),
        sa.UniqueConstraint(
            "provider", "external_entity_type", "external_identifier", name="uq_external_identity"
        ),
    )
    op.create_index("ix_external_identity_entity_id", "external_identity", ["entity_id"])

    op.create_table(
        "canonical_version",
        sa.Column("version_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_entity.entity_id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("system_from", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("system_to", sa.DateTime(timezone=True)),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column(
            "supersedes_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_version.version_id"),
        ),
        sa.CheckConstraint("version_number > 0", name="ck_canonical_version_positive"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name="ck_canonical_version_effective_range",
        ),
        sa.CheckConstraint(
            "system_to IS NULL OR system_to > system_from", name="ck_canonical_version_system_range"
        ),
        sa.UniqueConstraint("entity_id", "version_number", name="uq_canonical_entity_version"),
    )
    op.create_index("ix_canonical_version_entity_id", "canonical_version", ["entity_id"])
    op.create_index("ix_canonical_version_effective_from", "canonical_version", ["effective_from"])
    op.create_index("ix_canonical_version_system_from", "canonical_version", ["system_from"])
    op.create_index("ix_canonical_version_system_to", "canonical_version", ["system_to"])

    op.create_table(
        "provenance_link",
        sa.Column("provenance_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_version.version_id"),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_evidence.evidence_id"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(length=128), nullable=False),
        sa.Column("transformation_reference", sa.String(length=512)),
        sa.Column("authority_decision_reference", sa.String(length=512)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "version_id", "evidence_id", "relationship_type", name="uq_provenance_link"
        ),
    )
    op.create_index("ix_provenance_link_version_id", "provenance_link", ["version_id"])
    op.create_index("ix_provenance_link_evidence_id", "provenance_link", ["evidence_id"])

    op.create_table(
        "quality_assessment",
        sa.Column("quality_assessment_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_type", sa.String(length=128), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quality_state", sa.String(length=128), nullable=False),
        sa.Column("rule_reference", sa.String(length=512)),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("details_reference", sa.String(length=1024)),
    )
    op.create_index("ix_quality_assessment_subject_id", "quality_assessment", ["subject_id"])
    op.create_index("ix_quality_assessment_quality_state", "quality_assessment", ["quality_state"])

    op.create_table(
        "current_projection",
        sa.Column("projection_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("projection_type", sa.String(length=128), nullable=False),
        sa.Column(
            "entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_entity.entity_id"),
            nullable=False,
        ),
        sa.Column(
            "current_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("canonical_version.version_id"),
            nullable=False,
        ),
        sa.Column("projection_version", sa.Integer(), nullable=False),
        sa.Column("projected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("projection_type", "entity_id", name="uq_current_projection"),
    )
    op.create_index("ix_current_projection_entity_id", "current_projection", ["entity_id"])

    op.create_table(
        "idempotency_record",
        sa.Column("operation_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operation_scope", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=512), nullable=False),
        sa.Column("operation_version", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("result_reference", sa.String(length=1024)),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint(
            "operation_scope", "idempotency_key", "operation_version", name="uq_idempotency_key"
        ),
    )

    op.create_table(
        "event_outbox",
        sa.Column("outbox_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("aggregate_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregate_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=256), nullable=False),
        sa.Column("event_version", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("causation_id", sa.String(length=128)),
        sa.Column("publication_state", sa.String(length=64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_event_outbox_aggregate_id", "event_outbox", ["aggregate_id"])


def downgrade() -> None:
    op.drop_index("ix_event_outbox_aggregate_id", table_name="event_outbox")
    op.drop_table("event_outbox")
    op.drop_table("idempotency_record")
    op.drop_index("ix_current_projection_entity_id", table_name="current_projection")
    op.drop_table("current_projection")
    op.drop_index("ix_quality_assessment_quality_state", table_name="quality_assessment")
    op.drop_index("ix_quality_assessment_subject_id", table_name="quality_assessment")
    op.drop_table("quality_assessment")
    op.drop_index("ix_provenance_link_evidence_id", table_name="provenance_link")
    op.drop_index("ix_provenance_link_version_id", table_name="provenance_link")
    op.drop_table("provenance_link")
    op.drop_index("ix_canonical_version_system_to", table_name="canonical_version")
    op.drop_index("ix_canonical_version_system_from", table_name="canonical_version")
    op.drop_index("ix_canonical_version_effective_from", table_name="canonical_version")
    op.drop_index("ix_canonical_version_entity_id", table_name="canonical_version")
    op.drop_table("canonical_version")
    op.drop_index("ix_external_identity_entity_id", table_name="external_identity")
    op.drop_table("external_identity")
    op.drop_index("ix_canonical_entity_entity_type", table_name="canonical_entity")
    op.drop_table("canonical_entity")
    op.drop_table("source_evidence")
