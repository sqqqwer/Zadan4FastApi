
"""Record invite invalidation by onboarding compensation.

Revision ID: auth_0002
Revises: auth_0001
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "auth_0002"
down_revision: str | Sequence[str] | None = "auth_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow invalidation to be distinguished from invite use and expiry."""
    op.add_column("invite", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True), schema="auth")


def downgrade() -> None:
    """Remove the explicit invalidation timestamp."""
    op.drop_column("invite", "invalidated_at", schema="auth")
