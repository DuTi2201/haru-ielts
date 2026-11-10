"""billing: admin prices, feature rules, discount codes, feature passes

Revision ID: d9f3b7e1a2c4
Revises: c8e2a6d4f9b1

- billing.product_setting: an admin's price / "was" price / name / blurb / on-sale for a catalogue
  product (the defaults stay in app/services/billing/catalog.py).
- billing.feature_rule: how each AI speaking feature is sold (free, a one-time trial, pass only);
  billing.setting: the trial's size (live minutes, presentation tries);
  conversation_session.allowed_seconds: how long a live session was allowed to run (a trial
  session that is never finished counts as all of it).
- billing.coupon: discount codes; billing.orders gains list_amount, discount and coupon_code.
- billing.entitlement may now hold a 'feature_pass' (Haru Nói).
Nothing existing changes meaning: old orders have no discount, no rule row means the default rule.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d9f3b7e1a2c4"
down_revision = "c8e2a6d4f9b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_setting",
        sa.Column("product_code", sa.String(40), primary_key=True),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("compare_at", sa.Integer(), nullable=True),
        sa.Column("title_vi", sa.String(120), nullable=True),
        sa.Column("blurb_vi", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="billing",
    )
    op.create_table(
        "feature_rule",
        sa.Column("feature", sa.String(20), primary_key=True),
        sa.Column("mode", sa.String(8), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("mode in ('free','trial','paid')", name="ck_billing_feature_rule_mode"),
        schema="billing",
    )
    op.create_table(
        "setting",
        sa.Column("key", sa.String(40), primary_key=True),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="billing",
    )
    op.add_column("conversation_session", sa.Column("allowed_seconds", sa.Integer(), nullable=True))
    op.create_table(
        "coupon",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("percent_off", sa.SmallInteger(), nullable=True),
        sa.Column("amount_off", sa.Integer(), nullable=True),
        sa.Column("product_codes", postgresql.JSONB(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("once_per_learner", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("(percent_off is null) <> (amount_off is null)", name="ck_billing_coupon_one_kind"),
        sa.CheckConstraint("percent_off is null or (percent_off between 1 and 90)", name="ck_billing_coupon_percent"),
        sa.CheckConstraint("amount_off is null or amount_off > 0", name="ck_billing_coupon_amount"),
        schema="billing",
    )
    op.add_column("orders", sa.Column("list_amount", sa.Integer(), nullable=True), schema="billing")
    op.add_column("orders", sa.Column("discount", sa.Integer(), nullable=False, server_default="0"), schema="billing")
    op.add_column("orders", sa.Column("coupon_code", sa.String(32), nullable=True), schema="billing")
    op.create_index("ix_billing_orders_coupon_code", "orders", ["coupon_code"], schema="billing")
    op.drop_constraint("ck_billing_entitlement_kind", "entitlement", schema="billing", type_="check")
    op.create_check_constraint(
        "ck_billing_entitlement_kind", "entitlement", "kind in ('lesson_pack','exam_pass','feature_pass','grant')", schema="billing"
    )


def downgrade() -> None:
    op.drop_constraint("ck_billing_entitlement_kind", "entitlement", schema="billing", type_="check")
    op.create_check_constraint(
        "ck_billing_entitlement_kind", "entitlement", "kind in ('lesson_pack','exam_pass','grant')", schema="billing"
    )
    op.drop_index("ix_billing_orders_coupon_code", table_name="orders", schema="billing")
    op.drop_column("orders", "coupon_code", schema="billing")
    op.drop_column("orders", "discount", schema="billing")
    op.drop_column("orders", "list_amount", schema="billing")
    op.drop_column("conversation_session", "allowed_seconds")
    op.drop_table("setting", schema="billing")
    op.drop_table("coupon", schema="billing")
    op.drop_table("feature_rule", schema="billing")
    op.drop_table("product_setting", schema="billing")
