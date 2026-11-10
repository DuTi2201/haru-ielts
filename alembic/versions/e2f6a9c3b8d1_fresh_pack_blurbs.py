"""The price page showed lesson ranges and a session count left over from admin edits made before
the alphabet lesson moved every lesson down one place and before Haru Nói 90 ngày went to 300
minutes ("Bài 42–71", "khoảng 25 buổi"). Those numbers belong to the code
(app/services/billing/catalog.py: they follow LESSON_SHIFT and `minutes`), so an override that
spells out a lesson range or a number of sessions is cleared and the default text applies again.
An admin can still set any text from the admin screen.

Revision ID: e2f6a9c3b8d1
Revises: d7a3c9e1f5b2
"""
from alembic import op

revision = "e2f6a9c3b8d1"
down_revision = "d7a3c9e1f5b2"
branch_labels = None
depends_on = None

NUMBERED = ("pack_sinh_hoat_2", "pack_9_41", "pack_viet_54", "pack_42_71", "pack_all", "speak_30", "speak_90")


def upgrade() -> None:
    codes = ", ".join(f"'{c}'" for c in NUMBERED)
    op.execute(
        "UPDATE billing.product_setting SET blurb_vi = NULL "
        f"WHERE product_code IN ({codes}) AND (blurb_vi ~ 'Bài [0-9]' OR blurb_vi LIKE '%buổi%')"
    )
    # "Lộ trình Sơ – Trung cấp" was renamed: Sơ cấp is the free lessons and Nền tảng
    op.execute("UPDATE billing.product_setting SET title_vi = NULL WHERE product_code = 'pack_9_41' AND title_vi LIKE '%Sơ%'")


def downgrade() -> None:
    pass
