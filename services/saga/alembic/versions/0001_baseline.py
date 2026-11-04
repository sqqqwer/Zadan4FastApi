
"""Create the saga schema, onboarding state, inbox and outbox.

Revision ID: saga_0001
Revises:
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "saga_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create storage in a new saga database."""
    op.execute("CREATE SCHEMA IF NOT EXISTS saga")
    op.create_table(
        "saga",
        sa.Column("saga_id", sa.Uuid(), nullable=False),
        sa.Column("invite_id", sa.Uuid(), nullable=False),
        sa.Column(
            "state",
            sa.Enum(
                "RUNNING", "COMPENSATING", "COMPLETED", "COMPENSATED",
                name="saga_state", schema="saga",
            ),
            nullable=False,
        ),
        sa.Column(
            "step",
            sa.Enum(
                "ORG_ASSIGN", "TASK_CREATE", "TASK_CANCEL", "ORG_UNASSIGN", "INVITE_INVALIDATE", "DONE",
                name="saga_step", schema="saga",
            ),
            nullable=False,
        ),
        sa.Column("context", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("saga_id"),
        sa.UniqueConstraint("invite_id"),
        schema="saga",
    )
    op.create_index("ix_saga_state_updated_at", "saga", ["state", "updated_at"], schema="saga")
    op.create_table(
        "inbox_messages",
        sa.Column("consumer_name", sa.String(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("consumer_name", "event_id"),
        schema="saga",
    )
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("dedup_key", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("envelope", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
        sa.UniqueConstraint("dedup_key"),
        schema="saga",
    )
    op.create_index(
        "ix_outbox_messages_unpublished_created_at", "outbox_messages", ["created_at"],
        schema="saga", postgresql_where=sa.text("published_at IS NULL"),
    )


def downgrade() -> None:
    """Remove only the saga service's own schema."""
    op.drop_table("outbox_messages", schema="saga")
    op.drop_table("inbox_messages", schema="saga")
    op.drop_table("saga", schema="saga")
    sa.Enum(name="saga_step", schema="saga").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="saga_state", schema="saga").drop(op.get_bind(), checkfirst=False)
    op.execute("DROP SCHEMA saga")
