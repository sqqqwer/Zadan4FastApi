
"""Store the employee onboarding target in its invite.

Revision ID: auth_0003
Revises: auth_0002
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "auth_0003"
down_revision: str | Sequence[str] | None = "auth_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep existing invite purposes and legacy rows without inventing org references."""
    op.add_column("invite", sa.Column("position_id", sa.Uuid(), nullable=True), schema="auth")
    op.add_column("invite", sa.Column("struct_id", sa.Uuid(), nullable=True), schema="auth")


def downgrade() -> None:
    """Remove onboarding references without modifying accounts or users."""
    op.drop_column("invite", "struct_id", schema="auth")
    op.drop_column("invite", "position_id", schema="auth")
