"""Pricing of October 2026: the admin's overrides on the products whose price was redone, and on
the size of the free trial, are cleared so the new defaults (app/services/billing/catalog.py,
features.py) apply. An admin can set any of them again from the admin screen.

Revision ID: b4d1f7a2c9e3
Revises: a7c3e9b1d5f2
"""
from alembic import op

revision = "b4d1f7a2c9e3"
down_revision = "a7c3e9b1d5f2"
branch_labels = None
depends_on = None

REPRICED = ("pack_sinh_hoat_2", "pack_viet_54", "exam_pass_30", "exam_pass_90")


def upgrade() -> None:
    codes = ", ".join(f"'{c}'" for c in REPRICED)
    op.execute(f"UPDATE billing.product_setting SET amount = NULL, compare_at = NULL, blurb_vi = NULL WHERE product_code IN ({codes})")
    op.execute("DELETE FROM billing.setting WHERE key IN ('live_trial_minutes', 'present_trial_tries')")


def downgrade() -> None:
    # the old overrides are not kept: an admin sets them again from the admin screen
    pass
