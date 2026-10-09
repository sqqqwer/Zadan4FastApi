"""create ltree.

Revision ID: 023e8b878434
Revises: 81041540e888
Create Date: 2026-09-13 21:07:41.747733

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "023e8b878434"
down_revision: str | Sequence[str] | None = "81041540e888"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS ltree")
