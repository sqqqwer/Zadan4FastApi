
"""Remember welcome task ownership and cancellation.

Revision ID: tasks_0002
Revises: tasks_0001
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "tasks_0002"
down_revision: str | Sequence[str] | None = "tasks_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Retain cancellation even when a task was never created or was deleted."""
    op.create_table(
        "onboarding_task",
        sa.Column("saga_id", sa.Uuid(), nullable=False),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("cancelled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("saga_id"),
        schema="tasks",
    )


def downgrade() -> None:
    """Remove welcome task and cancellation records."""
    op.drop_table("onboarding_task", schema="tasks")
