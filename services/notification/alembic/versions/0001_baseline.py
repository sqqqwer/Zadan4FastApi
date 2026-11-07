"""Create the notification schema and inbox.

Revision ID: notification_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "notification_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create storage in a new notification database."""
    op.execute("CREATE SCHEMA IF NOT EXISTS notification")
    op.create_table(
        "inbox_messages",
        sa.Column("consumer_name", sa.String(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("consumer_name", "event_id"),
        schema="notification",
    )


def downgrade() -> None:
    """Remove only the notification service schema."""
    op.drop_table("inbox_messages", schema="notification")
    op.execute("DROP SCHEMA notification")
