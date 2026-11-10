"""Backup of the database to the bucket and the way back (services/db_backup).

The database part runs against the local test Postgres in a schema of its own (`bk_test`), the
bucket is a dict; the credential is fake."""
import datetime as dt
import json
import unittest
from unittest import mock

from sqlalchemy import create_engine, text

from app.core import celery_app as celery_module
from app.core.config import settings
from app.services import audio_store, db_backup
from app.workers import tasks

SCHEMA = "bk_test"


class MemoryStore:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key, data, content_type):
        self.objects[key] = data

    def get(self, key):
        return self.objects.get(key)

    def list(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))

    def delete(self, key):
        self.objects.pop(key, None)


def at(day):
    return dt.datetime.fromisoformat(f"{day}T20:00:00+00:00")


class PruneTests(unittest.TestCase):
    def store(self, days, half=()):
        s = MemoryStore()
        for d in days:
            s.objects[f"backup/{d}/public.t.copy.gz"] = b"x"
            s.objects[f"backup/{d}/manifest.json"] = b"{}"
        for d in half:
            s.objects[f"backup/{d}/public.t.copy.gz"] = b"x"
        s.objects["backup/latest.json"] = b"{}"
        return s

    def test_only_the_newest_complete_days_stay(self):
        s = self.store(["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"])
        self.assertEqual(db_backup.prune(s, keep=2), ["2026-10-01", "2026-10-02"])
        self.assertEqual({k.split("/")[1] for k in s.objects}, {"2026-10-03", "2026-10-04", "latest.json"})

    def test_a_half_written_old_day_goes_but_one_in_progress_stays(self):
        s = self.store(["2026-10-02", "2026-10-03"], half=["2026-10-01", "2026-10-04"])
        db_backup.prune(s, keep=2)
        days = {k.split("/")[1] for k in s.objects}
        self.assertNotIn("2026-10-01", days)
        self.assertIn("2026-10-04", days)

    def test_the_pointer_is_never_deleted(self):
        s = self.store(["2026-10-01"])
        db_backup.prune(s, keep=1)
        self.assertIn("backup/latest.json", s.objects)


@unittest.skipUnless(settings.DATABASE_URL, "needs the test database")
class RoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(settings.SYNC_DATABASE_URL)
        with cls.engine.connect() as c:
            cls.superuser = c.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")).scalar()

    def setUp(self):
        with self.engine.begin() as c:
            c.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
            c.execute(text(f"CREATE SCHEMA {SCHEMA}"))
            c.execute(text(f"CREATE TABLE {SCHEMA}.parent (id serial PRIMARY KEY, name text NOT NULL, meta jsonb, blob bytea)"))
            c.execute(
                text(
                    f"CREATE TABLE {SCHEMA}.child (id serial PRIMARY KEY, parent_id int NOT NULL REFERENCES {SCHEMA}.parent(id), "
                    f"tags text[], note text, total int GENERATED ALWAYS AS (id * 2) STORED)"
                )
            )
            c.execute(text(f"CREATE TABLE {SCHEMA}.empty (id int)"))
            c.execute(text(f"CREATE TABLE {SCHEMA}.events (id int NOT NULL, what text) PARTITION BY RANGE (id)"))
            c.execute(text(f"CREATE TABLE {SCHEMA}.events_a PARTITION OF {SCHEMA}.events FOR VALUES FROM (0) TO (10)"))
            c.execute(text(f"CREATE TABLE {SCHEMA}.events_b PARTITION OF {SCHEMA}.events FOR VALUES FROM (10) TO (20)"))
            c.execute(text(f"INSERT INTO {SCHEMA}.events VALUES (1, 'a'), (11, 'b'), (12, 'c')"))
            c.execute(
                text(f"INSERT INTO {SCHEMA}.parent (name, meta, blob) VALUES (:n, CAST(:m AS jsonb), :b), ('two', NULL, NULL)"),
                {"n": "tab\there\nnew\\line", "m": json.dumps({"k": [1, 2, {"x": "ü"}]}), "b": b"\x00\x01\xff"},
            )
            c.execute(
                text(f"INSERT INTO {SCHEMA}.child (parent_id, tags, note) VALUES (1, ARRAY['a','b c'], 'x'), (2, NULL, NULL)")
            )
        self.addCleanup(self.drop)
        self.store = MemoryStore()

    def drop(self):
        with self.engine.begin() as c:
            c.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))

    def snapshot(self):
        with self.engine.connect() as c:
            return {
                "parent": c.execute(text(f"SELECT id, name, meta, blob FROM {SCHEMA}.parent ORDER BY id")).all(),
                "child": c.execute(text(f"SELECT id, parent_id, tags, note, total FROM {SCHEMA}.child ORDER BY id")).all(),
                "events": c.execute(text(f"SELECT id, what, tableoid::regclass::text FROM {SCHEMA}.events ORDER BY id")).all(),
            }

    def backup(self, day="2026-10-14"):
        return db_backup.run_backup(self.engine, self.store, schemas=[SCHEMA], now=at(day))

    def test_a_backup_lists_its_files_and_the_manifest_comes_last(self):
        out = self.backup()
        self.assertEqual((out["day"], out["tables"], out["rows"]), ("2026-10-14", 4, 7))  # the partitioned table counts once, with its rows
        names = sorted(self.store.objects)
        self.assertIn(f"backup/2026-10-14/{SCHEMA}.parent.copy.gz", names)
        self.assertIn("backup/2026-10-14/manifest.json", names)
        manifest = json.loads(self.store.objects["backup/2026-10-14/manifest.json"])
        child = next(t for t in manifest["tables"] if t["table"] == f"{SCHEMA}.child")
        self.assertEqual(child["columns"], ["id", "parent_id", "tags", "note"])  # the generated column is not copied
        self.assertEqual(json.loads(self.store.objects["backup/latest.json"]), {"day": "2026-10-14"})

    def test_the_audio_caches_and_the_system_are_not_in_a_full_backup(self):
        with self.engine.connect() as c, c.connection.cursor() as cur:
            names = {f"{s}.{t}" for s, t in db_backup.list_tables(cur)}
        self.assertFalse(names & db_backup.SKIP_TABLES)
        self.assertFalse({n for n in names if n.startswith(("pg_catalog.", "information_schema."))})

    def test_everything_comes_back_exactly(self):
        if not self.superuser:
            self.skipTest("loading needs a superuser")
        before = self.snapshot()
        self.backup()
        with self.engine.begin() as c:
            c.execute(text(f"TRUNCATE {SCHEMA}.child, {SCHEMA}.parent, {SCHEMA}.events RESTART IDENTITY"))
        # the schema-limited test restores only its own tables: fake the revision check away
        manifest = json.loads(self.store.objects["backup/2026-10-14/manifest.json"])
        with mock.patch.object(db_backup, "alembic_revision", return_value=manifest["alembic_revision"]):
            out = db_backup.restore_backup(self.engine, self.store)
        self.assertEqual((out["tables"], out["rows"]), (4, 7))
        self.assertEqual(self.snapshot(), before)
        with self.engine.begin() as c:  # the sequences continue after the highest id
            new_id = c.execute(text(f"INSERT INTO {SCHEMA}.parent (name) VALUES ('three') RETURNING id")).scalar()
        self.assertEqual(new_id, 3)

    def test_a_database_with_rows_is_refused_unless_forced(self):
        if not self.superuser:
            self.skipTest("loading needs a superuser")
        self.backup()
        manifest = json.loads(self.store.objects["backup/2026-10-14/manifest.json"])
        with mock.patch.object(db_backup, "alembic_revision", return_value=manifest["alembic_revision"]):
            with self.assertRaises(db_backup.RestoreError) as caught:
                db_backup.restore_backup(self.engine, self.store)
            self.assertIn("--force", str(caught.exception))
            before = self.snapshot()
            db_backup.restore_backup(self.engine, self.store, force=True)
        self.assertEqual(self.snapshot(), before)

    def test_another_revision_or_a_damaged_file_changes_nothing(self):
        if not self.superuser:
            self.skipTest("loading needs a superuser")
        self.backup()
        before = self.snapshot()
        manifest = json.loads(self.store.objects["backup/2026-10-14/manifest.json"])
        with mock.patch.object(db_backup, "alembic_revision", return_value="other"):
            with self.assertRaises(db_backup.RestoreError) as caught:
                db_backup.restore_backup(self.engine, self.store, force=True)
        self.assertIn("revision", str(caught.exception))
        self.store.objects[f"backup/2026-10-14/{SCHEMA}.parent.copy.gz"] = b"damaged"
        with mock.patch.object(db_backup, "alembic_revision", return_value=manifest["alembic_revision"]):
            with self.assertRaises(db_backup.RestoreError) as caught:
                db_backup.restore_backup(self.engine, self.store, force=True)
        self.assertIn("damaged", str(caught.exception))
        self.assertEqual(self.snapshot(), before)  # nothing was emptied before the check

    def test_an_unfinished_day_is_not_a_backup(self):
        self.backup()
        self.store.delete("backup/2026-10-14/manifest.json")
        with self.assertRaises(db_backup.RestoreError):
            db_backup.read_manifest(self.store, "2026-10-14")

    def test_the_session_is_left_as_it_was_found(self):
        self.backup()
        with self.engine.connect() as c:
            self.assertEqual(c.execute(text("SHOW transaction_read_only")).scalar(), "off")
            self.assertEqual(c.execute(text("SHOW transaction_isolation")).scalar(), "read committed")


class WiringTests(unittest.TestCase):
    def test_the_task_does_nothing_without_the_bucket(self):
        with mock.patch.object(audio_store.settings, "AUDIO_STORAGE", "db"):
            self.assertEqual(tasks.backup_database.run(), {"skipped": True})

    def test_the_task_backs_up_to_the_bucket(self):
        for name, value in (("AUDIO_STORAGE", "gcs"), ("AUDIO_GCS_BUCKET", "b"), ("AUDIO_GCS_CREDENTIALS", "fake-test-credential")):
            p = mock.patch.object(audio_store.settings, name, value)
            p.start()
            self.addCleanup(p.stop)
        with mock.patch.object(db_backup, "run_backup", return_value={"day": "d"}) as run:
            self.assertEqual(tasks.backup_database.run(), {"day": "d"})
        self.assertIsInstance(run.call_args.args[1], db_backup.GcsStore)

    def test_it_is_scheduled_every_night(self):
        entry = celery_module.celery_app.conf.beat_schedule["backup-database"]
        self.assertEqual(entry["task"], "app.workers.tasks.backup_database")
        self.assertEqual((entry["schedule"].hour, entry["schedule"].minute), ({20}, {0}))

    def test_the_gcs_store_uses_the_bucket_calls(self):
        store = db_backup.GcsStore()
        with mock.patch.object(audio_store, "gcs_put") as put, mock.patch.object(audio_store, "gcs_list", return_value=["a"]) as lst, mock.patch.object(
            audio_store, "gcs_delete"
        ) as dele, mock.patch.object(audio_store, "gcs_get", return_value=b"x"):
            store.put("k", b"d", "application/gzip")
            self.assertEqual((store.list("backup/"), store.get("k")), (["a"], b"x"))
            store.delete("k")
        put.assert_called_once_with("k", b"d", "application/gzip")
        lst.assert_called_once_with("backup/")
        dele.assert_called_once_with("k")


if __name__ == "__main__":
    unittest.main()
