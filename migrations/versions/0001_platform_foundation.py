"""platform foundation

Revision ID: 0001_platform_foundation
Revises:
Create Date: 2026-08-31
"""

from collections.abc import Sequence

revision: str = "0001_platform_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Establish migration lineage without introducing athlete-domain semantics."""


def downgrade() -> None:
    """Reverse the no-op foundation revision."""
