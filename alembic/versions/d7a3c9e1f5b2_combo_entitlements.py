"""Combos: one paid order can grant several products (a combo grants each of its products), so an
order may now have one entitlement per product instead of one in all. Paying twice still grants
nothing twice: (order, product) stays unique.

Revision ID: d7a3c9e1f5b2
Revises: c5e2a8f1d4b7
"""
from alembic import op

revision = "d7a3c9e1f5b2"
down_revision = "c5e2a8f1d4b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_billing_entitlement_order", "entitlement", schema="billing", type_="unique")
    op.create_unique_constraint(
        "uq_billing_entitlement_order_product", "entitlement", ["order_id", "product_code"], schema="billing"
    )


def downgrade() -> None:
    op.drop_constraint("uq_billing_entitlement_order_product", "entitlement", schema="billing", type_="unique")
    op.create_unique_constraint("uq_billing_entitlement_order", "entitlement", ["order_id"], schema="billing")
