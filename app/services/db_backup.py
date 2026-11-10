"""Backup of the database to the private bucket, and the way back.

Why this exists: the Postgres volume has no backups of its own (Railway's plan allows none), and
it already filled up once. A copy in the bucket (the one the audio and pictures live in) is the
only second copy of the learners' progress and of the imported content.

How: every table is written with COPY ... TO STDOUT (Postgres's own text format, so every type —
jsonb, bytea, arrays, vectors — comes back exactly), gzipped, and uploaded as
`backup/<UTC day>/<schema>.<table>.copy.gz`, all from ONE snapshot (REPEATABLE READ, read-only).
`manifest.json` goes up LAST, and only a day that has its manifest counts as a backup; then
`backup/latest.json` points to it and days older than KEEP_DAYS are deleted.

Why not pg_dump: the worker image has no matching client (the server is Postgres 18), and a
version-matched one is a heavy thing to add for ~a few MB of data.

Left out (made again on demand, see migration a9d3e7c1b5f4): the four audio caches. Pictures and
the audio files themselves are objects in the bucket already; only their rows are in the backup.

Restore (into a database brought to the same Alembic revision, `alembic upgrade head`):
    python -m app.services.db_backup restore [--day YYYY-MM-DD] --force --yes
`alembic upgrade head` already seeds a few tables, so a fresh database needs --force: it empties
the tables in the backup, then loads them. Without --force it refuses a database that has rows. It
also refuses a database at another revision, checks every file's SHA-256, loads everything in one transaction with foreign-key
triggers off (`session_replication_role = replica`: needs a superuser, which Railway's is), and
sets the sequences after the highest id."""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import io
import json
import logging
import tempfile
from typing import Protocol

from psycopg2 import sql

from app.core.config import settings
from app.services import audio_store

log = logging.getLogger(__name__)

PREFIX = settings.BACKUP_GCS_PREFIX or "backup-ielts"
KEEP_DAYS = 14
# made again on demand; alembic_version is recorded in the manifest instead
SKIP_TABLES = frozenset(
    {
        "audio.lecture_audio",
        "audio.text_audio",
        "audio.corpus_item_audio",
        "audio.vocab_item_audio",
        "public.alembic_version",
    }
)


class RestoreError(RuntimeError):
    """The backup cannot be loaded here (the message says why and what to do)."""


class Store(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes | None: ...
    def list(self, prefix: str) -> list[str]: ...
    def delete(self, key: str) -> None: ...


class GcsStore:
    """The private bucket (settings.AUDIO_GCS_BUCKET / AUDIO_GCS_CREDENTIALS)."""

    def put(self, key: str, data: bytes, content_type: str) -> None:
        audio_store.gcs_put(key, data, content_type)

    def get(self, key: str) -> bytes | None:
        return audio_store.gcs_get(key)

    def list(self, prefix: str) -> list[str]:
        return audio_store.gcs_list(prefix)

    def delete(self, key: str) -> None:
        audio_store.gcs_delete(key)


# ------------------------------------------------------------------ what is in the database --
def list_tables(cur, schemas: list[str] | None = None) -> list[tuple[str, str]]:
    """(schema, table) of every table that belongs to the application (not the system catalogue, not
    an extension's), minus SKIP_TABLES. A partitioned table is one entry: its partitions are copied
    through it, and loaded back into the right partition."""
    query = (
        "SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE c.relkind IN ('r', 'p') AND NOT c.relispartition "
        "AND n.nspname <> 'information_schema' AND left(n.nspname, 3) <> 'pg_' "
        "AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = c.oid AND d.deptype = 'e') "
    )
    params: tuple = ()
    if schemas is not None:
        query += "AND n.nspname = ANY(%s) "
        params = (list(schemas),)
    cur.execute(query + "ORDER BY 1, 2", params)
    return [(s, t) for s, t in cur.fetchall() if f"{s}.{t}" not in SKIP_TABLES]


def table_columns(cur, schema: str, table: str) -> list[str]:
    """Columns that hold data (not dropped, not generated), in order."""
    cur.execute(
        "SELECT a.attname FROM pg_attribute a WHERE a.attrelid = %s::regclass AND a.attnum > 0 "
        "AND NOT a.attisdropped AND a.attgenerated = '' ORDER BY a.attnum",
        (f'"{schema}"."{table}"',),
    )
    return [r[0] for r in cur.fetchall()]


def alembic_revision(cur) -> str | None:
    cur.execute("SELECT to_regclass('alembic_version')")
    if cur.fetchone()[0] is None:
        return None
    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None


def _ident(schema: str, table: str) -> sql.Composable:
    return sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(table))


def _copy_out(cur, schema: str, table: str, columns: list[str]) -> tuple[bytes, int]:
    """One table as gzip(COPY text) and its row count."""
    # COPY (SELECT ...) rather than COPY table: it is the only form that reads a partitioned table
    stmt = sql.SQL("COPY (SELECT {} FROM {}) TO STDOUT").format(
        sql.SQL(", ").join(sql.Identifier(c) for c in columns), _ident(schema, table)
    )
    with tempfile.TemporaryFile() as tmp:
        with gzip.GzipFile(fileobj=tmp, mode="wb", compresslevel=6) as gz:
            cur.copy_expert(stmt.as_string(cur), gz)
        rows = max(cur.rowcount, 0)
        tmp.seek(0)
        return tmp.read(), rows


# --------------------------------------------------------------------------------- backup --
def _days(store: Store) -> list[str]:
    """UTC days that have a complete backup (a manifest), oldest first."""
    days = set()
    for name in store.list(f"{PREFIX}/"):
        parts = name.split("/")
        if len(parts) == 3 and parts[2] == "manifest.json":
            days.add(parts[1])
    return sorted(days)


def prune(store: Store, keep: int = KEEP_DAYS) -> list[str]:
    """Delete every backup but the `keep` newest complete ones, and any half-written day older than
    those (a day still being written, newer than them, is left alone). Returns the days removed."""
    kept = set(_days(store)[-max(keep, 1):])
    oldest = min(kept) if kept else None
    removed = set()
    for name in store.list(f"{PREFIX}/"):
        parts = name.split("/")
        if len(parts) == 3 and parts[1] not in kept and (oldest is None or parts[1] < oldest):
            store.delete(name)
            removed.add(parts[1])
    return sorted(removed)


def run_backup(engine, store: Store, *, schemas: list[str] | None = None, now: dt.datetime | None = None, keep: int = KEEP_DAYS) -> dict:
    """Back up every table of the application. `engine` is a synchronous SQLAlchemy engine."""
    now = now or dt.datetime.now(dt.timezone.utc)
    day = now.astimezone(dt.timezone.utc).date().isoformat()
    raw = engine.raw_connection()
    conn = raw.driver_connection
    entries: list[dict] = []
    try:
        conn.set_session(isolation_level="REPEATABLE READ", readonly=True)
        cur = conn.cursor()
        revision = alembic_revision(cur)
        for schema, table in list_tables(cur, schemas):
            columns = table_columns(cur, schema, table)
            data, rows = _copy_out(cur, schema, table, columns)
            key = f"{PREFIX}/{day}/{schema}.{table}.copy.gz"
            store.put(key, data, "application/gzip")
            entries.append(
                {
                    "table": f"{schema}.{table}",
                    "columns": columns,
                    "rows": rows,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "key": key,
                }
            )
        server_version = conn.server_version
    finally:
        try:
            conn.rollback()
            conn.set_session(isolation_level="READ COMMITTED", readonly=False)
        finally:
            raw.close()
    manifest = {
        "version": 1,
        "day": day,
        "created_at": now.isoformat(),
        "alembic_revision": revision,
        "server_version": server_version,
        "tables": entries,
    }
    store.put(f"{PREFIX}/{day}/manifest.json", json.dumps(manifest, indent=1).encode(), "application/json")
    store.put(f"{PREFIX}/latest.json", json.dumps({"day": day}).encode(), "application/json")
    removed = prune(store, keep)
    total = sum(e["bytes"] for e in entries)
    log.info("[backup] %s: %s tables, %s rows, %.1f MB; removed %s", day, len(entries), sum(e["rows"] for e in entries), total / 1e6, removed)
    return {
        "day": day,
        "tables": len(entries),
        "rows": sum(e["rows"] for e in entries),
        "mb": round(total / 1e6, 2),
        "removed": removed,
    }


# -------------------------------------------------------------------------------- restore --
def read_manifest(store: Store, day: str | None = None) -> dict:
    if day is None:
        pointer = store.get(f"{PREFIX}/latest.json")
        if not pointer:
            raise RestoreError("there is no backup in the bucket (backup/latest.json is missing)")
        day = json.loads(pointer)["day"]
    raw = store.get(f"{PREFIX}/{day}/manifest.json")
    if not raw:
        raise RestoreError(f"the backup of {day} is missing or was never finished (no manifest.json)")
    return json.loads(raw)


def _reset_sequences(cur, schema: str, table: str, columns: list[str]) -> None:
    for column in columns:
        cur.execute("SELECT pg_get_serial_sequence(%s, %s)", (f'"{schema}"."{table}"', column))
        seq = cur.fetchone()[0]
        if seq:
            cur.execute(
                sql.SQL("SELECT setval(%s, COALESCE(max({col}), 1), max({col}) IS NOT NULL) FROM {tbl}").format(
                    col=sql.Identifier(column), tbl=_ident(schema, table)
                ),
                (seq,),
            )


def restore_backup(engine, store: Store, *, day: str | None = None, force: bool = False) -> dict:
    """Load a backup into this (empty, same-revision) database. All or nothing."""
    manifest = read_manifest(store, day)
    raw = engine.raw_connection()
    conn = raw.driver_connection
    try:
        cur = conn.cursor()
        here = alembic_revision(cur)
        if here != manifest["alembic_revision"]:
            raise RestoreError(
                f"this database is at revision {here}, the backup at {manifest['alembic_revision']}: "
                f"run the migrations to exactly that revision first (alembic upgrade {manifest['alembic_revision']})"
            )
        tables = [(e["table"].split(".", 1), e) for e in manifest["tables"]]
        if not force:
            full = []
            for (schema, table), _entry in tables:
                cur.execute(sql.SQL("SELECT EXISTS (SELECT 1 FROM {})").format(_ident(schema, table)))
                if cur.fetchone()[0]:
                    full.append(f"{schema}.{table}")
            if full:
                raise RestoreError(f"these tables already have rows ({', '.join(full[:5])}…); use --force to empty them first")
        # download and verify everything BEFORE touching the database
        blobs = {}
        for _name, entry in tables:
            data = store.get(entry["key"])
            if data is None or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise RestoreError(f"{entry['key']} is missing or damaged (checksum does not match)")
            blobs[entry["key"]] = data
        try:
            cur.execute("SET LOCAL session_replication_role = replica")
        except Exception as exc:  # noqa: BLE001
            raise RestoreError("loading needs a superuser (session_replication_role): " + str(exc).splitlines()[0]) from exc
        if force:
            cur.execute(
                sql.SQL("TRUNCATE TABLE {}").format(sql.SQL(", ").join(_ident(s, t) for (s, t), _e in tables))
            )
        rows = 0
        for (schema, table), entry in tables:
            stmt = sql.SQL("COPY {} ({}) FROM STDIN").format(
                _ident(schema, table), sql.SQL(", ").join(sql.Identifier(c) for c in entry["columns"])
            )
            with gzip.GzipFile(fileobj=io.BytesIO(blobs[entry["key"]]), mode="rb") as gz:
                cur.copy_expert(stmt.as_string(cur), gz)
            rows += max(cur.rowcount, 0)
            _reset_sequences(cur, schema, table, entry["columns"])
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        raw.close()
    return {"day": manifest["day"], "tables": len(tables), "rows": rows}


# ------------------------------------------------------------------------------------ CLI --
def main(argv: list[str] | None = None) -> int:
    import argparse

    from sqlalchemy import create_engine

    from app.core.config import settings

    parser = argparse.ArgumentParser(prog="python -m app.services.db_backup")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("backup", help="back up now")
    rest = sub.add_parser("restore", help="load a backup into the database named by DATABASE_URL")
    rest.add_argument("--day", help="UTC day (YYYY-MM-DD); default: the latest")
    rest.add_argument("--force", action="store_true", help="empty the tables first")
    rest.add_argument("--yes", action="store_true", help="really do it")
    args = parser.parse_args(argv)

    if audio_store.backend() != "gcs":
        print("The bucket is not configured: set AUDIO_STORAGE=gcs, AUDIO_GCS_BUCKET and AUDIO_GCS_CREDENTIALS.")
        return 2
    engine = create_engine(settings.SYNC_DATABASE_URL)
    store = GcsStore()
    if args.command == "backup":
        print(json.dumps(run_backup(engine, store), indent=1))
        return 0
    target = engine.url.render_as_string(hide_password=True)
    manifest = read_manifest(store, args.day)
    print(f"Backup {manifest['day']} ({len(manifest['tables'])} tables) -> {target}")
    if not args.yes:
        print("Nothing done. Add --yes to load it.")
        return 1
    try:
        print(json.dumps(restore_backup(engine, store, day=args.day, force=args.force), indent=1))
    except RestoreError as exc:
        print(f"Not restored: {exc}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
