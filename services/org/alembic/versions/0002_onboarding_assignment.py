
"""Remember onboarding assignment ownership and cancellation.

Revision ID: org_0002
Revises: org_0001
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "org_0002"
down_revision: str | Sequence[str] | None = "org_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist saga results independently of deleted positions and bindings."""
    op.create_table(
        "onboarding_assignment",
        sa.Column("saga_id", sa.Uuid(), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("binding_id", sa.Uuid(), nullable=True),
        sa.Column("cancelled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("saga_id"),
        schema="org",
    )


def downgrade() -> None:
    """Remove assignment and cancellation records."""
    op.drop_table("onboarding_assignment", schema="org")
