"""lesson pictures: a picture can be hidden without losing it

* content.scene_image.hidden — an editor can take a picture off the lessons (it looked
  wrong) without deleting it; the next "Tạo ảnh" then does not draw it again.
* content.scene_image.kind — where the picture is used (lesson | vocab | grammar | scene),
  for the Studio listing; NULL on a row made before the column existed.

Revision ID: a2d7f4b8c1e6
Revises: e7a3c9d5b1f8
Create Date: 2026-10-06 01:20:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'a2d7f4b8c1e6'
down_revision = 'e7a3c9d5b1f8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'scene_image',
        sa.Column('hidden', sa.Boolean(), server_default=sa.false(), nullable=False),
        schema='content',
    )
    op.add_column('scene_image', sa.Column('kind', sa.String(length=16), nullable=True), schema='content')


def downgrade() -> None:
    op.drop_column('scene_image', 'kind', schema='content')
    op.drop_column('scene_image', 'hidden', schema='content')
