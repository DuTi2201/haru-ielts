"""Empty the recordings kept in Postgres, once, to give the 500 MB volume back

Revision ID: a9d3e7c1b5f4
Revises: c5e9a3b7d1f2

The volume filled up with audio (a lesson's podcast is ~40 MB) and Postgres could not even write
its log any more. Every recording in these four tables is a CACHE: the next request for the same
lesson / sentence / word / text voices it again and files it (now in the bucket, see
services/audio_store.py), so nothing that cannot be remade is lost. Old rows already moved to the
bucket lose their link; their objects stay there, harmless, and are overwritten by the new ones.

TRUNCATE, not DELETE: it writes no log for the rows and hands the disk space back at once, which a
DELETE (every page logged whole, space only returned by a later VACUUM FULL) cannot do on a full disk.
Nothing refers to these tables with a foreign key.

Before it, the write-ahead log is moved on to its next (already allocated) file: with the volume at
100% the file Postgres was writing had nowhere to grow, and TRUNCATE itself needs a few blocks for
the new empty files. The old WAL file is given back at the next checkpoint, which makes room.
"""
import logging

from alembic import op

revision = "a9d3e7c1b5f4"
down_revision = "c5e9a3b7d1f2"
branch_labels = None
depends_on = None


log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    try:
        with op.get_context().autocommit_block():
            op.execute("SELECT pg_switch_wal()")  # needs a superuser; harmless anywhere else
    except Exception as exc:  # noqa: BLE001 - not a superuser, a replica…: the TRUNCATE below decides
        log.warning("pg_switch_wal skipped: %s", str(exc).splitlines()[0][:120])
    op.execute("SET LOCAL lock_timeout = '60s'")
    op.execute(
        "TRUNCATE TABLE audio.lecture_audio, audio.text_audio, audio.corpus_item_audio, audio.vocab_item_audio"
    )


def downgrade() -> None:
    """Recordings cannot be brought back; they are made again on demand."""
