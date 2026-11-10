"""anti-abuse for the free trial: device / network traces, trial uses, blocked e-mail domains

Revision ID: e1c5a9f3d7b6
Revises: d9f3b7e1a2c4

- profiles.email_key: the address as its inbox sees it (Gmail ignores dots and "+tag", most mail
  ignores "+tag"), so "an.nguyen+2@gmail.com" cannot sign up again beside "annguyen@gmail.com".
  Filled for the accounts already there. Not unique: old duplicates, if any, stay as they are.
- billing.account_signal: which browser (a random id the app keeps) and which network (the IP)
  an account was seen from, both as a keyed hash, never the raw value.
- billing.trial_use: every start on the free trial (live seconds granted, or one presentation try),
  with the browser and network it came from: one trial per browser, a soft cap per network, and the
  day's total for the whole system.
- billing.blocked_email_domain: throwaway-mail domains an admin adds on top of the bundled list.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e1c5a9f3d7b6"
down_revision = "d9f3b7e1a2c4"
branch_labels = None
depends_on = None


def _email_key(email: str) -> str:
    # a copy of app.services.abuse.email_key as it was when this ran (a migration never imports app code)
    local, _, domain = (email or "").strip().lower().rpartition("@")
    if not local:
        return (email or "").strip().lower()
    local = local.split("+", 1)[0] or local
    if domain in ("gmail.com", "googlemail.com"):
        local, domain = local.replace(".", ""), "gmail.com"
    return f"{local}@{domain}"


def upgrade() -> None:
    op.add_column("profiles", sa.Column("email_key", sa.String(255), nullable=True))
    op.create_index("ix_profiles_email_key", "profiles", ["email_key"])
    bind = op.get_bind()
    rows = bind.execute(sa.text("select id, email from profiles")).all()
    for pid, email in rows:
        bind.execute(sa.text("update profiles set email_key = :k where id = :i"), {"k": _email_key(email), "i": pid})

    op.create_table(
        "account_signal",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("value", sa.String(64), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("seen_count", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("kind in ('device','ip')", name="ck_billing_account_signal_kind"),
        sa.UniqueConstraint("profile_id", "kind", "value", name="uq_billing_account_signal"),
        schema="billing",
    )
    op.create_index("ix_billing_account_signal_value", "account_signal", ["kind", "value"], schema="billing")

    op.create_table(
        "trial_use",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature", sa.String(20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("device", sa.String(64), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="billing",
    )
    op.create_index("ix_billing_trial_use_created", "trial_use", ["created_at"], schema="billing")
    op.create_index("ix_billing_trial_use_device", "trial_use", ["device"], schema="billing")
    op.create_index("ix_billing_trial_use_ip", "trial_use", ["ip", "created_at"], schema="billing")
    op.create_index("ix_billing_trial_use_profile", "trial_use", ["profile_id"], schema="billing")

    op.create_table(
        "blocked_email_domain",
        sa.Column("domain", sa.String(253), primary_key=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        schema="billing",
    )


def downgrade() -> None:
    op.drop_table("blocked_email_domain", schema="billing")
    op.drop_index("ix_billing_trial_use_profile", table_name="trial_use", schema="billing")
    op.drop_index("ix_billing_trial_use_ip", table_name="trial_use", schema="billing")
    op.drop_index("ix_billing_trial_use_device", table_name="trial_use", schema="billing")
    op.drop_index("ix_billing_trial_use_created", table_name="trial_use", schema="billing")
    op.drop_table("trial_use", schema="billing")
    op.drop_index("ix_billing_account_signal_value", table_name="account_signal", schema="billing")
    op.drop_table("account_signal", schema="billing")
    op.drop_index("ix_profiles_email_key", table_name="profiles")
    op.drop_column("profiles", "email_key")
