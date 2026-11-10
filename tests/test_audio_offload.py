"""Lesson recordings in the private bucket instead of the 500 MB Postgres volume: where a new
recording is filed, how a played one is read back, and the one-off move of those already in rows.

No network, no database: the bucket and the sessions are stand-ins, and the credential is fake."""
import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException

from app.api.routers import audio, content, lesson_images
from app.core import celery_app as celery_module
from app.models import CorpusItemAudio, LectureAudio, SceneImage, VocabItemAudio
from app.services import audio_store, job_events
from app.workers import tasks

FAKE_CRED = "fake-test-credential"


def gcs_on(test):
    for name, value in (("AUDIO_STORAGE", "gcs"), ("AUDIO_GCS_BUCKET", "haru-audio"), ("AUDIO_GCS_CREDENTIALS", FAKE_CRED)):
        p = mock.patch.object(audio_store.settings, name, value)
        p.start()
        test.addCleanup(p.stop)


ALL_OFFLOADED = (LectureAudio, tasks.TextAudio, CorpusItemAudio, VocabItemAudio, SceneImage)


def pk(row):
    return row.cache_key if hasattr(row, "mime_type") else row.id


def picture_row(**changes):
    base = dict(
        cache_key="lesson:3:banner", mime_type="image/webp", storage="db", object_key=None, data=b"WEBP", created_at=1,
    )
    return SimpleNamespace(**{**base, **changes})


def lecture_row(**changes):
    base = dict(
        id="r1", cache_key="podcast:lesson:33:ko-female-1", storage="db", opus_key=None, aac_key=None,
        opus_data=b"OPUS", aac_data=b"AAC", created_at=1,
    )
    return SimpleNamespace(**{**base, **changes})


class FileAwayTests(unittest.TestCase):
    def test_without_the_bucket_the_bytes_stay_in_the_row(self):
        with mock.patch.object(audio_store.settings, "AUDIO_STORAGE", "db"):
            out = audio_store.file_away("lecture", "k", b"O", b"A")
        self.assertEqual(out, {"storage": "db", "opus_key": None, "aac_key": None, "opus_data": b"O", "aac_data": b"A"})

    def test_with_the_bucket_both_files_are_uploaded_and_the_row_keeps_only_links(self):
        gcs_on(self)
        with mock.patch.object(audio_store, "gcs_put") as put:
            out = audio_store.file_away("lecture", "podcast:lesson:33:v", b"O", b"A")
        self.assertEqual(out["storage"], "gcs")
        self.assertEqual(out["opus_key"], "lecture/podcast/lesson/33/v.opus")
        self.assertEqual(out["aac_key"], "lecture/podcast/lesson/33/v.aac")
        self.assertIsNone(out["opus_data"])
        self.assertIsNone(out["aac_data"])
        self.assertEqual([c.args[0] for c in put.call_args_list], [out["opus_key"], out["aac_key"]])

    def test_a_failed_upload_keeps_the_audio_in_the_row(self):
        gcs_on(self)
        with mock.patch.object(audio_store, "gcs_put", side_effect=audio_store.StoreError("down")):
            out = audio_store.file_away("lecture", "k", b"O", b"A")
        self.assertEqual((out["storage"], out["opus_data"], out["aac_data"]), ("db", b"O", b"A"))

    def test_the_lecture_model_has_the_bucket_columns(self):
        for name in ("storage", "opus_key", "aac_key", "opus_data", "aac_data"):
            self.assertIn(name, LectureAudio.__table__.c)


class ReadRowTests(unittest.TestCase):
    def setUp(self):
        audio_store._cache.clear()
        audio_store._cache_size = 0

    def test_a_row_in_the_database_is_read_from_its_columns(self):
        row = lecture_row()
        self.assertEqual(audio_store.read_row(row, "opus"), b"OPUS")
        self.assertEqual(audio_store.read_row(row, "aac"), b"AAC")

    def test_a_row_in_the_bucket_is_fetched_once_for_many_ranges(self):
        row = lecture_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        with mock.patch.object(audio_store, "gcs_get", return_value=b"FROM-BUCKET") as get:
            for _ in range(3):
                self.assertEqual(audio_store.read_row(row, "aac"), b"FROM-BUCKET")
        get.assert_called_once_with("a")

    def test_the_memory_cache_stays_within_its_cap(self):
        with mock.patch.object(audio_store, "_CACHE_MAX_BYTES", 10), mock.patch.object(audio_store, "gcs_get", return_value=b"123456"):
            audio_store.gcs_get_cached("a")
            audio_store.gcs_get_cached("b")
        self.assertEqual(list(audio_store._cache), ["b"])
        self.assertEqual(audio_store._cache_size, 6)

    def test_a_missing_object_or_key_is_none(self):
        row = lecture_row(storage="gcs", opus_key=None, aac_key=None, opus_data=None, aac_data=None)
        self.assertIsNone(audio_store.read_row(row, "opus"))
        with mock.patch.object(audio_store, "gcs_get", return_value=None):
            self.assertIsNone(audio_store.read_row(lecture_row(storage="gcs", opus_key="o"), "opus"))


class StreamLectureTests(unittest.IsolatedAsyncioTestCase):
    def db(self, row):
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = row
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(return_value=res)
        return db

    def request(self, range_header=None):
        return SimpleNamespace(headers={"range": range_header} if range_header else {})

    async def test_a_podcast_in_the_bucket_is_served_whole_and_by_range(self):
        row = lecture_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        audio_store._cache.clear()
        with mock.patch.object(audio_store, "gcs_get", return_value=b"0123456789"):
            res = await audio.stream_lecture_audio("podcast:lesson:33.aac", self.request(), self.db(row))
            self.assertEqual((res.status_code, res.body), (200, b"0123456789"))
            res = await audio.stream_lecture_audio("podcast:lesson:33.aac", self.request("bytes=2-4"), self.db(row))
            self.assertEqual((res.status_code, res.body), (206, b"234"))

    async def test_a_podcast_still_in_the_row_is_served_as_before(self):
        res = await audio.stream_lecture_audio("podcast:lesson:33.opus", self.request(), self.db(lecture_row()))
        self.assertEqual(res.body, b"OPUS")

    async def test_an_unreachable_bucket_is_503_not_a_wrong_answer(self):
        row = lecture_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        with mock.patch.object(audio_store, "gcs_get", side_effect=audio_store.StoreError("down")):
            with self.assertRaises(HTTPException) as caught:
                await audio.stream_lecture_audio("podcast:lesson:33.opus", self.request(), self.db(row))
        self.assertEqual(caught.exception.status_code, 503)

    async def test_an_empty_row_is_404(self):
        row = lecture_row(opus_data=None, aac_data=None)
        with self.assertRaises(HTTPException) as caught:
            await audio.stream_lecture_audio("podcast:lesson:33.opus", self.request(), self.db(row))
        self.assertEqual(caught.exception.status_code, 404)


class PictureStoreTests(unittest.TestCase):
    def test_without_the_bucket_a_picture_stays_in_its_row(self):
        with mock.patch.object(audio_store.settings, "AUDIO_STORAGE", "db"):
            out = audio_store.file_image("k", b"W", "image/webp")
        self.assertEqual(out, {"storage": "db", "object_key": None, "data": b"W"})

    def test_with_the_bucket_the_row_keeps_only_the_name_of_the_object(self):
        gcs_on(self)
        with mock.patch.object(audio_store, "gcs_put") as put:
            out = audio_store.file_image("lesson:3:banner", b"W", "image/webp")
        self.assertEqual(out, {"storage": "gcs", "object_key": "img/lesson:3:banner.webp", "data": None})
        put.assert_called_once_with("img/lesson:3:banner.webp", b"W", "image/webp")

    def test_a_failed_upload_keeps_the_drawing_in_the_row(self):
        gcs_on(self)
        with mock.patch.object(audio_store, "gcs_put", side_effect=audio_store.StoreError("down")):
            out = audio_store.file_image("k", b"W", "image/png")
        self.assertEqual((out["storage"], out["data"]), ("db", b"W"))

    def test_a_picture_is_read_from_its_row_or_from_the_bucket_never_from_the_memory_cache(self):
        self.assertEqual(audio_store.read_image(picture_row()), b"WEBP")
        row = picture_row(storage="gcs", object_key="img/x.webp", data=None)
        with mock.patch.object(audio_store, "gcs_get", side_effect=[b"v1", b"v2"]) as get:
            self.assertEqual(audio_store.read_image(row), b"v1")
            self.assertEqual(audio_store.read_image(row), b"v2")  # drawn again meanwhile: no stale copy
        self.assertEqual(get.call_count, 2)
        self.assertIsNone(audio_store.read_image(picture_row(storage="gcs", object_key=None, data=None)))

    def test_offload_uploads_before_the_row_lets_go_and_a_failure_changes_nothing(self):
        row = picture_row()
        with mock.patch.object(audio_store, "gcs_put") as put:
            self.assertEqual(audio_store.offload_image(row), 4)
        put.assert_called_once_with("img/lesson:3:banner.webp", b"WEBP", "image/webp")
        self.assertEqual((row.storage, row.object_key, row.data), ("gcs", "img/lesson:3:banner.webp", None))
        row = picture_row()
        with mock.patch.object(audio_store, "gcs_put", side_effect=audio_store.StoreError("down")):
            with self.assertRaises(audio_store.StoreError):
                audio_store.offload_image(row)
        self.assertEqual((row.storage, row.object_key, row.data), ("db", None, b"WEBP"))

    def test_the_models_have_the_bucket_columns(self):
        for name in ("storage", "object_key", "data"):
            self.assertIn(name, SceneImage.__table__.c)
        for model in (CorpusItemAudio, VocabItemAudio):
            for name in ("storage", "opus_key", "aac_key"):
                self.assertIn(name, model.__table__.c)
            self.assertTrue(model.__table__.c.opus_data.nullable and model.__table__.c.aac_data.nullable)


class PictureRouteTests(unittest.IsolatedAsyncioTestCase):
    def db(self, row):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=row)
        return db

    async def test_a_picture_in_the_bucket_is_served_with_its_type_and_long_cache(self):
        row = picture_row(storage="gcs", object_key="img/x.webp", data=None)
        with mock.patch.object(audio_store, "gcs_get", return_value=b"FROM-BUCKET"):
            res = await content.get_scene_image("lesson:3:banner", self.db(row))
        self.assertEqual((res.body, res.media_type), (b"FROM-BUCKET", "image/webp"))
        self.assertIn("immutable", res.headers["cache-control"])

    async def test_a_picture_still_in_the_row_is_served_as_before(self):
        res = await content.get_scene_image("k", self.db(picture_row()))
        self.assertEqual(res.body, b"WEBP")

    async def test_unreachable_bucket_is_503_and_a_missing_object_is_404(self):
        row = picture_row(storage="gcs", object_key="img/x.webp", data=None)
        with mock.patch.object(audio_store, "gcs_get", side_effect=audio_store.StoreError("down")):
            with self.assertRaises(HTTPException) as caught:
                await content.get_scene_image("k", self.db(row))
        self.assertEqual(caught.exception.status_code, 503)
        with mock.patch.object(audio_store, "gcs_get", return_value=None):
            with self.assertRaises(HTTPException) as caught:
                await content.get_scene_image("k", self.db(row))
        self.assertEqual(caught.exception.status_code, 404)

    def test_a_copy_is_a_picture_of_its_own_with_its_own_object(self):
        gcs_on(self)
        source = picture_row(storage="gcs", object_key="img/src.webp", data=None, model="gemini")
        slot = SimpleNamespace(key="vocab:7", prompt="p", kind="vocab")
        with mock.patch.object(audio_store, "gcs_get", return_value=b"BYTES"), mock.patch.object(audio_store, "gcs_put") as put:
            copy = lesson_images._copy_of(source, slot)
        put.assert_called_once_with("img/vocab:7.webp", b"BYTES", "image/webp")
        self.assertEqual((copy.cache_key, copy.storage, copy.object_key, copy.data), ("vocab:7", "gcs", "img/vocab:7.webp", None))

    def test_a_copy_of_a_picture_without_bytes_is_refused(self):
        source = picture_row(storage="gcs", object_key=None, data=None, model="gemini")
        with self.assertRaises(audio_store.StoreError):
            lesson_images._copy_of(source, SimpleNamespace(key="v", prompt="p", kind="vocab"))


class WordAudioRouteTests(unittest.IsolatedAsyncioTestCase):
    def db(self, row):
        res = mock.MagicMock()
        res.scalar_one_or_none.return_value = row
        db = mock.MagicMock()
        db.execute = mock.AsyncMock(return_value=res)
        return db

    async def test_a_sentence_and_a_word_in_the_bucket_are_served(self):
        row = lecture_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        request = SimpleNamespace(headers={})
        audio_store._cache.clear()
        with mock.patch.object(audio_store, "gcs_get", return_value=b"SOUND"):
            for stream in (audio.stream_corpus_audio, audio.stream_vocab_audio):
                res = await stream("abc:ko:v1.aac", request, self.db(row))
                self.assertEqual(res.body, b"SOUND")
                audio_store._cache.clear()
                audio_store._cache_size = 0

    async def test_an_unreachable_bucket_is_503(self):
        row = lecture_row(storage="gcs", opus_key="o", aac_key="a", opus_data=None, aac_data=None)
        audio_store._cache.clear()
        with mock.patch.object(audio_store, "gcs_get", side_effect=audio_store.StoreError("down")):
            with self.assertRaises(HTTPException) as caught:
                await audio.stream_vocab_audio("abc:ko:v1.opus", SimpleNamespace(headers={}), self.db(row))
        self.assertEqual(caught.exception.status_code, 503)


class OffloadRowTests(unittest.TestCase):
    def test_both_files_are_uploaded_before_the_row_lets_go_of_its_bytes(self):
        row = lecture_row()
        with mock.patch.object(audio_store, "gcs_put") as put:
            moved = audio_store.offload_row(row, "lecture")
        self.assertEqual(moved, 7)
        self.assertEqual((row.storage, row.opus_data, row.aac_data), ("gcs", None, None))
        self.assertEqual((row.opus_key, row.aac_key), ("lecture/podcast/lesson/33/ko-female-1.opus", "lecture/podcast/lesson/33/ko-female-1.aac"))
        self.assertEqual(put.call_count, 2)

    def test_a_failed_upload_leaves_the_row_exactly_as_it_was(self):
        row = lecture_row()
        with mock.patch.object(audio_store, "gcs_put", side_effect=[None, audio_store.StoreError("down")]):
            with self.assertRaises(audio_store.StoreError):
                audio_store.offload_row(row, "lecture")
        self.assertEqual((row.storage, row.opus_data, row.aac_data, row.opus_key, row.aac_key), ("db", b"OPUS", b"AAC", None, None))

    def test_a_row_without_aac_moves_only_its_opus(self):
        row = lecture_row(aac_data=None)
        with mock.patch.object(audio_store, "gcs_put") as put:
            audio_store.offload_row(row, "lecture")
        put.assert_called_once()
        self.assertIsNone(row.aac_key)

    def test_a_row_already_in_the_bucket_or_empty_is_left_alone(self):
        with mock.patch.object(audio_store, "gcs_put") as put:
            self.assertEqual(audio_store.offload_row(lecture_row(storage="gcs", opus_data=None, aac_data=None), "lecture"), 0)
            self.assertEqual(audio_store.offload_row(lecture_row(opus_data=None, aac_data=None), "lecture"), 0)
        put.assert_not_called()


class OffloadTaskTests(unittest.TestCase):
    def sessions(self, rows_by_model):
        """Session stand-in: the id query returns the ids of the model's rows, db.get its row."""
        outer = self

        class FakeSession:
            def __init__(self, _engine):
                self.model = None

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def execute(self, stmt):
                model = next(m for m in ALL_OFFLOADED if m.__tablename__ in str(stmt.get_final_froms()[0]))
                res = mock.MagicMock()
                res.scalars.return_value.all.return_value = [pk(r) for r in rows_by_model.get(model, [])]
                return res

            def get(self, model, row_id):
                return next(r for r in rows_by_model[model] if pk(r) == row_id)

            commit = mock.MagicMock()
            rollback = mock.MagicMock()

        return FakeSession

    def run_task(self, rows_by_model, put):
        engine = mock.MagicMock()
        with mock.patch.object(tasks, "Session", self.sessions(rows_by_model)), mock.patch.object(
            tasks, "_sync_engine", engine
        ), mock.patch.object(audio_store, "gcs_put", put):
            return tasks.offload_audio_to_gcs.run(), engine

    def test_it_does_nothing_without_the_bucket(self):
        with mock.patch.object(audio_store.settings, "AUDIO_STORAGE", "db"):
            self.assertEqual(tasks.offload_audio_to_gcs.run(), {"skipped": True})

    def test_it_moves_every_row_and_then_returns_the_space(self):
        gcs_on(self)
        rows = {tasks.LectureAudio: [lecture_row(id="a"), lecture_row(id="b", cache_key="k2")]}
        out, engine = self.run_task(rows, mock.MagicMock())
        self.assertEqual((out["moved"], out["failed"]), (2, 0))
        self.assertTrue(all(r.storage == "gcs" and r.opus_data is None for r in rows[tasks.LectureAudio]))
        conn = engine.connect.return_value.execution_options.return_value.__enter__.return_value
        conn.exec_driver_sql.assert_called_once_with("VACUUM FULL audio.lecture_audio")

    def test_pictures_and_sentence_and_word_recordings_are_moved_too(self):
        gcs_on(self)
        rows = {
            SceneImage: [picture_row()],
            CorpusItemAudio: [lecture_row(id="c1", cache_key="c")],
            VocabItemAudio: [lecture_row(id="v1", cache_key="v")],
        }
        out, engine = self.run_task(rows, mock.MagicMock())
        self.assertEqual((out["moved"], out["failed"]), (3, 0))
        self.assertEqual(rows[SceneImage][0].storage, "gcs")
        self.assertEqual(rows[CorpusItemAudio][0].opus_key, "word/c.opus")
        conn = engine.connect.return_value.execution_options.return_value.__enter__.return_value
        self.assertEqual(
            [c.args[0] for c in conn.exec_driver_sql.call_args_list],
            ["VACUUM FULL audio.corpus_item_audio", "VACUUM FULL audio.vocab_item_audio", "VACUUM FULL content.scene_image"],
        )

    def test_a_bucket_that_keeps_failing_stops_the_run_and_deletes_nothing(self):
        gcs_on(self)
        rows = {tasks.LectureAudio: [lecture_row(id=str(i), cache_key=f"k{i}") for i in range(6)]}
        put = mock.MagicMock(side_effect=audio_store.StoreError("down"))
        out, engine = self.run_task(rows, put)
        self.assertEqual(out["moved"], 0)
        self.assertEqual(put.call_count, 3)  # gave up after three in a row
        self.assertTrue(all(r.storage == "db" and r.opus_data == b"OPUS" for r in rows[tasks.LectureAudio]))
        engine.connect.assert_not_called()  # nothing moved, so no VACUUM


class WorkerBootTests(unittest.TestCase):
    def test_the_offload_is_queued_at_boot_only_when_the_bucket_is_on(self):
        with mock.patch.object(celery_module.celery_app, "send_task") as send:
            with mock.patch.object(audio_store.settings, "AUDIO_STORAGE", "db"):
                celery_module._offload_audio_when_worker_starts()
            send.assert_not_called()
            gcs_on(self)
            celery_module._offload_audio_when_worker_starts()
            self.assertEqual(
                [c.args[0] for c in send.call_args_list],
                ["app.workers.tasks.offload_audio_to_gcs", "app.workers.tasks.backup_database"],
            )


class ErrorMessageTests(unittest.TestCase):
    def test_a_full_disk_is_explained_and_the_sql_stays_out_of_sight(self):
        raw = '(psycopg2.errors.DiskFull) could not extend file: No space left on device [SQL: INSERT INTO audio.lecture_audio ...]'
        msg = job_events.public_error_message(raw)
        self.assertIn("hết dung lượng", msg)
        self.assertNotIn("SQL", msg)

    def test_any_other_database_error_is_hidden_too(self):
        self.assertNotIn("INSERT", job_events.public_error_message("(sqlalchemy.exc.IntegrityError) [SQL: INSERT INTO x]"))

    def test_an_ordinary_message_is_left_as_it_was(self):
        self.assertEqual(job_events.public_error_message("Gemini trả về rỗng"), "Gemini trả về rỗng")


if __name__ == "__main__":
    unittest.main()
