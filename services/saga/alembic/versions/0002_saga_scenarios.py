
"""Allow independent saga scenarios and scenario-specific step names.

Revision ID: saga_0002
Revises: saga_0001
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "saga_0002"
down_revision: str | Sequence[str] | None = "saga_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Preserve existing onboarding records while generalizing their storage."""
    op.add_column(
        "saga",
        sa.Column("saga_type", sa.Text(), server_default="employee_onboarding", nullable=False),
        schema="saga",
    )
    op.add_column("saga", sa.Column("business_key", sa.Text(), nullable=True), schema="saga")
    op.execute("UPDATE saga.saga SET business_key = invite_id::text")
    op.alter_column("saga", "business_key", existing_type=sa.Text(), nullable=False, schema="saga")
    op.alter_column("saga", "saga_type", existing_type=sa.Text(), server_default=None, schema="saga")
    op.create_unique_constraint("uq_saga_type_business_key", "saga", ["saga_type", "business_key"], schema="saga")
    op.drop_column("saga", "invite_id", schema="saga")
    op.alter_column(
        "saga", "step", type_=sa.Text(), postgresql_using="step::text", existing_nullable=False, schema="saga"
    )
    postgresql.ENUM(name="saga_step", schema="saga").drop(op.get_bind(), checkfirst=False)


def downgrade() -> None:
    """Restore onboarding-only storage when every record can still be represented."""
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM saga.saga WHERE saga_type <> 'employee_onboarding') THEN
                RAISE EXCEPTION 'Cannot downgrade saga_0002 while other saga scenarios exist';
            END IF;
        END $$;
    """)
    step_type = postgresql.ENUM(
        "ORG_ASSIGN",
        "TASK_CREATE",
        "TASK_CANCEL",
        "ORG_UNASSIGN",
        "INVITE_INVALIDATE",
        "DONE",
        name="saga_step",
        schema="saga",
        create_type=False,
    )
    step_type.create(op.get_bind(), checkfirst=False)
    op.alter_column(
        "saga",
        "step",
        existing_type=sa.Text(),
        type_=step_type,
        postgresql_using="step::saga.saga_step",
        existing_nullable=False,
        schema="saga",
    )
    op.add_column("saga", sa.Column("invite_id", sa.Uuid(), nullable=True), schema="saga")
    op.execute("UPDATE saga.saga SET invite_id = business_key::uuid")
    op.alter_column("saga", "invite_id", existing_type=sa.Uuid(), nullable=False, schema="saga")
    op.create_unique_constraint("saga_invite_id_key", "saga", ["invite_id"], schema="saga")
    op.drop_constraint("uq_saga_type_business_key", "saga", type_="unique", schema="saga")
    op.drop_column("saga", "business_key", schema="saga")
    op.drop_column("saga", "saga_type", schema="saga")
