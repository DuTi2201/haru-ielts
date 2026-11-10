"""Paid access: the `billing` schema (orders, payments, entitlements, claims)

Revision ID: c4e8a2f7d1b9
Revises: b6f2d8a4c0e7

Four new tables and nothing changed in the existing ones. Every account that exists today gets a
lifetime "all" grant (source "grandfather"), so switching BILLING_ENABLED on later never locks the
people already using the app out; accounts made after this migration start with the free lessons.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c4e8a2f7d1b9"
down_revision = "b6f2d8a4c0e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS billing")
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_code", sa.BigInteger(), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_code", sa.String(40), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("payment_link_id", sa.String(80), nullable=True),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("payment_info", postgresql.JSONB(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_ref", sa.String(80), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("order_code", name="orders_order_code_key"),
        sa.CheckConstraint(
            "status in ('PENDING','PAID','EXPIRED','CANCELLED','UNDERPAID','NEEDS_REVIEW')", name="ck_billing_order_status"
        ),
        sa.CheckConstraint("amount > 0", name="ck_billing_order_amount"),
        schema="billing",
    )
    op.create_index("ix_billing_orders_status", "orders", ["status"], schema="billing")
    op.create_index("ix_billing_orders_profile_created", "orders", ["profile_id", "created_at"], schema="billing")

    op.create_table(
        "payment_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("order_code", sa.BigInteger(), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("raw", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference", name="uq_billing_payment_event_reference"),
        schema="billing",
    )
    op.create_index("ix_billing_payment_event_order_code", "payment_event", ["order_code"], schema="billing")
    op.create_index("ix_billing_payment_event_order_id", "payment_event", ["order_id"], schema="billing")

    op.create_table(
        "entitlement",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("product_code", sa.String(40), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["billing.orders.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("order_id", name="uq_billing_entitlement_order"),
        sa.CheckConstraint("kind in ('lesson_pack','exam_pass','grant')", name="ck_billing_entitlement_kind"),
        schema="billing",
    )
    op.create_index("ix_billing_entitlement_profile_id", "entitlement", ["profile_id"], schema="billing")

    op.create_table(
        "claim",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("bank_ref", sa.String(80), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["billing.orders.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("status in ('open','resolved','rejected')", name="ck_billing_claim_status"),
        schema="billing",
    )
    op.create_index("ix_billing_claim_profile_id", "claim", ["profile_id"], schema="billing")
    op.create_index("ix_billing_claim_status", "claim", ["status"], schema="billing")

    # whoever is here now keeps everything
    op.execute(
        """
        INSERT INTO billing.entitlement (id, profile_id, kind, product_code, source, note)
        SELECT gen_random_uuid(), id, 'grant', 'all', 'grandfather', 'account existed before paid access'
        FROM profiles
        """
    )


def downgrade() -> None:
    for table in ("claim", "entitlement", "payment_event", "orders"):
        op.drop_table(table, schema="billing")
    op.execute("DROP SCHEMA IF EXISTS billing")
