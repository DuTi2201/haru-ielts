"""Lesson pictures: the plan (what is drawn where), the Gemini call (both endpoints, errors,
the WebP squeeze), what learners see, and the Studio endpoints and background run."""
import base64
import io
import json
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import httpx
from fastapi import HTTPException
from PIL import Image

from app.api.routers import content, lesson_images
from app.schemas import ImageGenerateRequest, ImageHideRequest
from app.services import lesson_image, lesson_image_db, lesson_seed
from app.workers import tasks

NOW = datetime(2026, 10, 6, 1, 0, tzinfo=timezone.utc)
BUNDLE = lesson_seed.load_all()
FAKE_KEY = "fake-test-credential"


def png(width=1200, height=800, mode="RGB", color=(200, 220, 255)) -> bytes:
    buf = io.BytesIO()
    Image.new(mode, (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def interactions_reply(data: bytes) -> dict:
    return {"id": "x", "output_image": {"data": b64(data), "mime_type": "image/png"}}


def classic_reply(data: bytes) -> dict:
    return {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": b64(data)}}]}}]}


def lesson_triples():
    return [(r.seed.slug, [v.hangul for v in r.seed.vocab], [g.pattern for g in r.seed.grammar]) for r in BUNDLE.lessons]


PILOT = 0


def slots_of(index=PILOT):
    r = BUNDLE.lessons[index]
    return lesson_image.lesson_slots(
        r.seed.slug, [v.hangul for v in r.seed.vocab], [g.pattern for g in r.seed.grammar], r.practice
    )


class PlanTests(unittest.TestCase):
    def test_every_picture_of_the_plan_belongs_to_a_real_lesson_item(self):
        self.assertEqual(lesson_image.check_plan(lesson_triples()), [])

    def test_every_topic_cover_names_a_real_topic(self):
        topics = {t for r in BUNDLE.lessons for t in ([r.seed.topic] if getattr(r.seed, "topic", None) else [])}
        self.assertEqual(lesson_image.check_plan(lesson_triples(), topics), [])

    def test_a_picture_that_points_at_nothing_is_reported(self):
        plan = lesson_image.Plan("v1", {"nope": "x" * 30}, {"없는 말": "y" * 30}, {"G": "short"})
        with mock.patch.object(lesson_image, "load_plan", return_value=plan):
            problems = lesson_image.check_plan(lesson_triples())
        self.assertEqual(len(problems), 4)
        self.assertTrue(any("'nope'" in p for p in problems))
        self.assertTrue(any("too short" in p for p in problems))

    def test_units_and_honorific_words_have_no_picture(self):
        plan = lesson_image.load_plan()
        for word in ("개", "벌", "켤레", "드시다 / 잡수시다", "서술체"):
            self.assertNotIn(word, plan.vocab)

    def test_a_charts_numbers_are_never_drawn_by_a_model(self):
        # chart/table data has no scene, so no slot is ever made for it
        for r in range(len(BUNDLE.lessons)):
            for s in slots_of(r):
                self.assertNotIn("chart", s.kind)

    def test_the_same_prompt_is_the_same_picture_whatever_the_model(self):
        a = lesson_image.scene_key("a man washes dishes")
        self.assertEqual(a, lesson_image.scene_key("  a man washes dishes "))
        self.assertNotEqual(a, lesson_image.scene_key("a woman washes dishes"))
        with mock.patch.object(lesson_image.settings, "GEMINI_MODEL_IMAGE", "another-model"):
            self.assertEqual(a, lesson_image.scene_key("a man washes dishes"))

    def test_a_new_house_style_draws_everything_again(self):
        old = lesson_image.scene_key("a man")
        plan = lesson_image.Plan("v2", {}, {}, {})
        with mock.patch.object(lesson_image, "load_plan", return_value=plan):
            self.assertNotEqual(old, lesson_image.scene_key("a man"))

    def test_the_prompt_asks_for_the_house_style_and_the_shape(self):
        text = lesson_image.build_prompt("A cat.", "16:9")
        self.assertIn("no text", text.lower())
        self.assertIn("A cat.", text)
        self.assertIn("16:9", text)


class ParsingTests(unittest.TestCase):
    def test_both_reply_shapes_are_understood(self):
        data = png(300, 200)
        for reply in (interactions_reply(data), classic_reply(data)):
            found = lesson_image.find_image(reply)
            self.assertIsNotNone(found)
            self.assertEqual(found[0], data)
            self.assertEqual(found[1], "image/png")

    def test_a_reply_without_a_picture_gives_nothing(self):
        self.assertIsNone(lesson_image.find_image({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "hi"}]}}]}))
        self.assertIsNone(lesson_image.find_image({"output_image": {"data": "abc", "mime_type": "image/png"}}))  # too short to be one

    def test_a_big_png_becomes_a_small_webp_within_the_size_limit(self):
        out = lesson_image.to_webp(png(1600, 900), 640)
        image = Image.open(io.BytesIO(out))
        self.assertEqual(image.format, "WEBP")
        self.assertEqual(max(image.size), 640)
        self.assertEqual(image.size, (640, 360))  # the shape is kept

    def test_a_transparent_picture_is_laid_flat_on_the_paper_colour(self):
        out = lesson_image.to_webp(png(100, 100, "RGBA", (0, 0, 0, 0)), 512)
        pixel = Image.open(io.BytesIO(out)).convert("RGB").getpixel((50, 50))
        self.assertGreater(min(pixel), 200)  # light, not black

    def test_something_that_is_not_a_picture_is_refused(self):
        with self.assertRaises(lesson_image.ImageGenError):
            lesson_image.to_webp(b"not an image at all", 512)


class GenerateTests(unittest.TestCase):
    def setUp(self):
        self.calls: list[httpx.Request] = []
        self.replies: list[httpx.Response] = []
        orig = httpx.Client

        def handler(request: httpx.Request) -> httpx.Response:
            self.calls.append(request)
            return self.replies.pop(0)

        transport = httpx.MockTransport(handler)
        patches = [
            mock.patch.object(lesson_image.httpx, "Client", lambda **kw: orig(transport=transport, **kw)),
            mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", True),
            mock.patch.object(lesson_image.settings, "GEMINI_MODEL_IMAGE", "img-model"),
            mock.patch.object(lesson_image.settings, "GEMINI_API_KEY", FAKE_KEY),
            mock.patch.object(lesson_image.settings, "GEMINI_IMAGE_API", "auto"),
            mock.patch.object(lesson_image, "_sleep", lambda s: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def reply(self, status=200, body=None):
        self.replies.append(httpx.Response(status, json=body if body is not None else {}))

    def test_the_interactions_endpoint_is_tried_first_and_the_key_stays_in_the_header(self):
        self.reply(200, interactions_reply(png()))
        data, mime = lesson_image.generate_image("A woman washes dishes.", "scene")
        self.assertEqual(mime, "image/webp")
        self.assertEqual(Image.open(io.BytesIO(data)).format, "WEBP")
        request = self.calls[0]
        self.assertTrue(str(request.url).endswith("/v1beta/interactions"))
        self.assertEqual(request.headers["x-goog-api-key"], FAKE_KEY)
        self.assertNotIn(FAKE_KEY, str(request.url))
        body = json.loads(request.content)
        self.assertEqual(body["model"], "img-model")
        self.assertIn("A woman washes dishes.", body["input"][0]["text"])

    def test_it_falls_back_to_generate_content_when_interactions_is_not_there(self):
        self.reply(404, {"error": {"message": "not found"}})
        self.reply(200, classic_reply(png()))
        data, mime = lesson_image.generate_image("A bus.", "vocab")
        self.assertEqual(mime, "image/webp")
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(str(self.calls[1].url).endswith("/models/img-model:generateContent"))
        body = json.loads(self.calls[1].content)
        self.assertEqual(body["generationConfig"]["responseModalities"], ["IMAGE"])
        self.assertEqual(body["generationConfig"]["imageConfig"]["aspectRatio"], "1:1")

    def test_one_endpoint_can_be_forced(self):
        with mock.patch.object(lesson_image.settings, "GEMINI_IMAGE_API", "generate_content"):
            self.reply(200, classic_reply(png()))
            lesson_image.generate_image("A bus.", "vocab")
        self.assertEqual(len(self.calls), 1)
        self.assertIn(":generateContent", str(self.calls[0].url))

    def test_a_busy_service_is_retried(self):
        self.reply(429, {"error": {"message": "slow down"}})
        self.reply(200, interactions_reply(png()))
        lesson_image.generate_image("A bus.")
        self.assertEqual(len(self.calls), 2)

    def test_a_bad_key_stops_everything_and_is_not_retried_or_fallen_back(self):
        self.reply(403, {"error": {"message": "API key not valid"}})
        with self.assertRaises(lesson_image.ImageGenError) as caught:
            lesson_image.generate_image("A bus.")
        self.assertTrue(caught.exception.fatal)
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn(FAKE_KEY, str(caught.exception))

    def test_a_refused_scene_is_blocked_not_fatal(self):
        self.reply(200, {"candidates": [{"finishReason": "IMAGE_SAFETY"}]})
        with self.assertRaises(lesson_image.ImageGenError) as caught:
            lesson_image.generate_image("A scene.")
        self.assertTrue(caught.exception.blocked)
        self.assertFalse(caught.exception.fatal)

    def test_a_reply_without_a_picture_is_an_error(self):
        self.reply(200, {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "sorry"}]}}]})
        with self.assertRaises(lesson_image.ImageGenError):
            lesson_image.generate_image("A scene.")

    def test_the_service_staying_busy_gives_up(self):
        for _ in range(3):
            self.reply(503, {"error": {"message": "overloaded"}})
        with self.assertRaises(lesson_image.ImageGenError):
            lesson_image.generate_image("A scene.")

    def test_it_does_nothing_while_off(self):
        with mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", False):
            with self.assertRaises(lesson_image.ImageGenDisabled):
                lesson_image.generate_image("A scene.")
        self.assertEqual(self.calls, [])

    def test_it_needs_a_model_name_and_a_key(self):
        with mock.patch.object(lesson_image.settings, "GEMINI_MODEL_IMAGE", ""):
            self.assertFalse(lesson_image.enabled())
        with mock.patch.object(lesson_image.settings, "GEMINI_API_KEY", ""):
            with self.assertRaises(lesson_image.ImageGenError) as caught:
                lesson_image.generate_image("A scene.")
        self.assertTrue(caught.exception.fatal)


class WorkSelectionTests(unittest.TestCase):
    def group(self, lesson_id, slots):
        return lesson_image_db.LessonSlots(lesson_id=lesson_id, slug=f"s{lesson_id}", title=f"L{lesson_id}", slots=slots)

    def slot(self, text, kind="vocab"):
        return lesson_image.Slot(kind=kind, label=text, prompt=text * 5)

    def test_only_what_is_missing_is_drawn(self):
        a, b, c = self.slot("a"), self.slot("b"), self.slot("c")
        work = lesson_image_db.pick_work([self.group(1, [a, b, c])], {b.key})
        self.assertEqual(work, [a, c])

    def test_a_picture_shared_by_two_lessons_is_drawn_once(self):
        a = self.slot("a")
        work = lesson_image_db.pick_work([self.group(1, [a]), self.group(2, [a])], set())
        self.assertEqual(work, [a])

    def test_keys_narrow_the_run_and_force_draws_again(self):
        a, b = self.slot("a"), self.slot("b")
        groups = [self.group(1, [a, b])]
        self.assertEqual(lesson_image_db.pick_work(groups, {a.key, b.key}, [a.key], False), [])
        self.assertEqual(lesson_image_db.pick_work(groups, {a.key, b.key}, [a.key], True), [a])

    def test_a_hidden_picture_is_not_a_gap(self):
        # the caller passes every stored key, hidden or not
        a = self.slot("a")
        self.assertEqual(lesson_image_db.pick_work([self.group(1, [a])], {a.key}), [])


class VisibleUrlTests(unittest.IsolatedAsyncioTestCase):
    def db(self, rows):
        db = mock.MagicMock()
        result = mock.MagicMock()
        result.all.return_value = rows
        db.execute = mock.AsyncMock(return_value=result)
        return db

    async def test_a_learner_gets_the_url_of_each_picture_that_exists(self):
        prompt = "A woman washes dishes at a sink."
        key = lesson_image.scene_key(prompt)
        db = self.db([(key, NOW)])
        with mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", True), mock.patch.object(
            lesson_image.settings, "GEMINI_MODEL_IMAGE", "img-model"
        ):
            urls = await lesson_image_db.visible_urls(db, [prompt, None, "  ", "Another one."])
        self.assertEqual(urls, {prompt: f"/api/v1/lessons/scene-image/{key}?v={int(NOW.timestamp())}"})
        sql = str(db.execute.call_args.args[0]).lower()
        self.assertIn("hidden is false", sql.replace("content.scene_image.hidden is false", "hidden is false"))

    async def test_nothing_is_looked_up_while_the_feature_is_off(self):
        db = self.db([])
        with mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", False):
            self.assertEqual(await lesson_image_db.visible_urls(db, ["x" * 30]), {})
        db.execute.assert_not_called()

    async def test_no_prompts_means_no_query(self):
        db = self.db([])
        with mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", True), mock.patch.object(
            lesson_image.settings, "GEMINI_MODEL_IMAGE", "m"
        ):
            self.assertEqual(await lesson_image_db.visible_urls(db, [None, ""]), {})
        db.execute.assert_not_called()

    def test_a_picture_drawn_again_gets_a_new_url(self):
        later = datetime(2026, 10, 7, tzinfo=timezone.utc)
        self.assertNotEqual(lesson_image_db.url_for("k", NOW), lesson_image_db.url_for("k", later))


class LessonEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_practice_set_carries_the_scene_pictures_that_exist(self):
        prompt = "A woman washes dishes at a sink."
        practice = {
            **BUNDLE.lessons[0].practice,
            "items": [
                *BUNDLE.lessons[0].practice["items"],
                {"id": "S99", "skill": "speaking", "type": "speak", "frames": [{"caption_vi": "x", "icons": ["🧼"], "image_prompt": prompt}]},
            ],
        }
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=SimpleNamespace(id=7, practice=practice))
        result = mock.MagicMock()
        result.all.return_value = [(lesson_image.scene_key(prompt), NOW)]
        lessons = mock.MagicMock()
        lessons.all.return_value = []  # the lessons named by the practice's support (none needed here)

        async def execute(stmt):
            return lessons if "FROM content.lesson" in str(stmt) else result

        db.execute = mock.AsyncMock(side_effect=execute)
        with mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", True), mock.patch.object(
            lesson_image.settings, "GEMINI_MODEL_IMAGE", "m"
        ):
            out = await content.get_lesson_practice(7, SimpleNamespace(headers={}), db)
        self.assertEqual(list(out.scene_images), [prompt])
        self.assertTrue(out.scene_images[prompt].startswith("/api/v1/lessons/scene-image/"))


# ------------------------------------------------------------------ Studio --
EDITOR = SimpleNamespace(id=uuid.UUID(int=9), role="editor")


def stored_row(key, hidden=False):
    return SimpleNamespace(cache_key=key, hidden=hidden, created_at=NOW, model="img-model")


class StudioEndpointTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        resolved = BUNDLE.lessons[PILOT]
        self.slots = [
            lesson_image.Slot("lesson", "Unit 1", "A calm desk with an English notebook."),
            lesson_image.Slot("vocab", "usually", "A clock showing morning routine."),
            lesson_image.Slot("vocab", "rarely", "A calendar with one mark."),
        ]
        self.group = lesson_image_db.LessonSlots(lesson_id=7, slug=resolved.seed.slug, title=resolved.seed.title, slots=self.slots)
        patches = [
            mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", True),
            mock.patch.object(lesson_image.settings, "GEMINI_MODEL_IMAGE", "img-model"),
            mock.patch.object(lesson_images.settings, "GEMINI_API_KEY", FAKE_KEY),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def patch_world(self, stored=None, active=None):
        stored = stored or {}
        return [
            mock.patch.object(lesson_image_db, "lesson_slots_async", mock.AsyncMock(return_value=[self.group])),
            mock.patch.object(lesson_images, "_stored", mock.AsyncMock(return_value=stored)),
            mock.patch.object(lesson_images, "_active_job", mock.AsyncMock(return_value=active)),
        ]

    async def run_with(self, patches, coro_fn):
        for p in patches:
            p.start()
        try:
            return await coro_fn()
        finally:
            for p in patches:
                p.stop()

    async def test_the_overview_counts_pictures_per_lesson(self):
        first, second = self.slots[0], self.slots[1]
        stored = {first.key: stored_row(first.key), second.key: stored_row(second.key, hidden=True)}
        out = await self.run_with(
            self.patch_world(stored),
            lambda: lesson_images.images_overview(mock.MagicMock(), EDITOR),
        )
        self.assertTrue(out.enabled)
        self.assertEqual(out.model, "img-model")
        row = out.lessons[0]
        self.assertEqual((row.total, row.have, row.hidden), (len(self.slots), 2, 1))
        self.assertEqual((out.total, out.have), (len(self.slots), 2))

    async def test_the_overview_counts_a_shared_picture_once(self):
        # two lessons wanting the same picture: one drawing, so one in the whole-curriculum count
        shared = self.slots[0]
        other = SimpleNamespace(
            lesson_id=8, slug="b", title="B", slots=[shared]
        )
        patches = [
            mock.patch.object(lesson_image_db, "lesson_slots_async", mock.AsyncMock(return_value=[self.group, other])),
            mock.patch.object(lesson_images, "_stored", mock.AsyncMock(return_value={})),
            mock.patch.object(lesson_images, "_active_job", mock.AsyncMock(return_value=None)),
        ]
        out = await self.run_with(patches, lambda: lesson_images.images_overview(mock.MagicMock(), EDITOR))
        self.assertEqual(out.total, len(self.slots))
        self.assertEqual(sum(l.total for l in out.lessons), len(self.slots) + 1)

    async def test_a_lessons_slots_show_url_prompt_and_state(self):
        first = self.slots[0]
        out = await self.run_with(
            self.patch_world({first.key: stored_row(first.key, hidden=True)}),
            lambda: lesson_images.lesson_images(7, mock.MagicMock(), EDITOR),
        )
        self.assertEqual(out.total, len(self.slots))
        self.assertEqual(out.have, 1)
        by_key = {s.key: s for s in out.slots}
        self.assertTrue(by_key[first.key].hidden)
        self.assertIn("scene-image", by_key[first.key].url)
        missing = next(s for s in out.slots if s.key != first.key)
        self.assertIsNone(missing.url)
        self.assertTrue(missing.prompt)

    async def test_an_unknown_lesson_is_a_404(self):
        with mock.patch.object(lesson_image_db, "lesson_slots_async", mock.AsyncMock(return_value=[])):
            with self.assertRaises(HTTPException) as caught:
                await lesson_images.lesson_images(99, mock.MagicMock(), EDITOR)
        self.assertEqual(caught.exception.status_code, 404)

    def db(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=SimpleNamespace(id=7))
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock()

        async def refresh(job):
            job.id = uuid.UUID(int=77)

        db.refresh = mock.AsyncMock(side_effect=refresh)
        return db

    async def test_pressing_the_button_queues_one_run_for_the_missing_pictures(self):
        db = self.db()
        patches = self.patch_world({self.slots[0].key: stored_row(self.slots[0].key)}) + [
            mock.patch.object(lesson_images, "generate_lesson_images")
        ]
        for p in patches:
            m = p.start()
        try:
            out = await lesson_images.start_drawing(ImageGenerateRequest(lesson_id=7), db, EDITOR)
            delay = lesson_images.generate_lesson_images.delay
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(out.job_id, uuid.UUID(int=77))
        self.assertEqual(out.status, "queued")
        job = db.add.call_args.args[0]
        self.assertEqual(job.type, "lesson_images")
        self.assertEqual(job.result, {"lesson_id": 7, "total": len(self.slots) - 1})
        delay.assert_called_once_with(str(uuid.UUID(int=77)), 7, None, False)

    async def test_a_run_already_going_is_returned_instead_of_starting_another(self):
        running = SimpleNamespace(id=uuid.UUID(int=5), status="running", result={"lesson_id": 7})
        patches = self.patch_world(active=running) + [mock.patch.object(lesson_images, "generate_lesson_images")]
        db = self.db()
        for p in patches:
            p.start()
        try:
            out = await lesson_images.start_drawing(ImageGenerateRequest(lesson_id=7), db, EDITOR)
            queued = lesson_images.generate_lesson_images.delay.called
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(out.job_id, uuid.UUID(int=5))
        self.assertFalse(queued)
        db.add.assert_not_called()

    async def test_when_everything_is_drawn_there_is_nothing_to_start(self):
        stored = {s.key: stored_row(s.key) for s in self.slots}
        with self.assertRaises(HTTPException) as caught:
            await self.run_with(
                self.patch_world(stored),
                lambda: lesson_images.start_drawing(ImageGenerateRequest(lesson_id=7), self.db(), EDITOR),
            )
        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(caught.exception.detail["code"], "nothing_missing")

    async def test_drawing_again_must_name_the_pictures(self):
        with self.assertRaises(HTTPException) as caught:
            await lesson_images.start_drawing(ImageGenerateRequest(lesson_id=7, force=True), self.db(), EDITOR)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(caught.exception.detail["code"], "force_needs_keys")

    async def test_drawing_again_a_named_picture_is_allowed_even_though_it_exists(self):
        first = self.slots[0]
        db = self.db()
        patches = self.patch_world({first.key: stored_row(first.key)}) + [mock.patch.object(lesson_images, "generate_lesson_images")]
        for p in patches:
            p.start()
        try:
            await lesson_images.start_drawing(ImageGenerateRequest(lesson_id=7, keys=[first.key], force=True), db, EDITOR)
            args = lesson_images.generate_lesson_images.delay.call_args.args
        finally:
            for p in patches:
                p.stop()
        self.assertEqual(args[2:], ([first.key], True))
        self.assertEqual(db.add.call_args.args[0].result["total"], 1)

    async def test_it_is_refused_while_the_feature_is_off(self):
        with mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", False):
            with self.assertRaises(HTTPException) as caught:
                await lesson_images.start_drawing(ImageGenerateRequest(lesson_id=7), self.db(), EDITOR)
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(caught.exception.detail["code"], "images_disabled")

    async def test_it_is_refused_without_a_gemini_key(self):
        with mock.patch.object(lesson_images.settings, "GEMINI_API_KEY", ""):
            with self.assertRaises(HTTPException) as caught:
                await lesson_images.start_drawing(ImageGenerateRequest(lesson_id=7), self.db(), EDITOR)
        self.assertEqual(caught.exception.detail["code"], "no_api_key")

    async def test_a_picture_can_be_hidden_and_put_back(self):
        row = SimpleNamespace(hidden=False)
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=row)
        db.commit = mock.AsyncMock()
        out = await lesson_images.hide_image("abc", ImageHideRequest(hidden=True), db, EDITOR)
        self.assertTrue(row.hidden)
        self.assertTrue(out.hidden)
        out = await lesson_images.hide_image("abc", ImageHideRequest(hidden=False), db, EDITOR)
        self.assertFalse(row.hidden)
        self.assertFalse(out.hidden)

    async def test_hiding_an_unknown_picture_is_a_404(self):
        db = mock.MagicMock()
        db.get = mock.AsyncMock(return_value=None)
        with self.assertRaises(HTTPException) as caught:
            await lesson_images.hide_image("nope", ImageHideRequest(hidden=True), db, EDITOR)
        self.assertEqual(caught.exception.status_code, 404)

    def test_only_editors_and_admins_may_use_these_endpoints(self):
        for route in lesson_images.router.routes:
            names = [d.call.__qualname__ for d in route.dependant.dependencies]
            self.assertTrue(any("require_role" in n for n in names), route.path)


class WorkerTests(unittest.TestCase):
    """The background run, with the database, Redis and Gemini replaced."""

    class FakeDB:
        def __init__(self, existing=()):
            self.rows = {k: SimpleNamespace(cache_key=k) for k in existing}
            self.added = []
            self.commits = 0

        def scalars(self, _query):
            return SimpleNamespace(all=lambda: list(self.rows))

        def get(self, _model, key):
            return self.rows.get(key)

        def add(self, row):
            self.added.append(row)
            self.rows[row.cache_key] = row

        def commit(self):
            self.commits += 1

        def rollback(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def setUp(self):
        self.slots = [
            lesson_image.Slot("vocab", f"w{i}", f"A picture number {i} with enough words.") for i in range(5)
        ]
        self.group = lesson_image_db.LessonSlots(lesson_id=7, slug="s", title="T", slots=self.slots)
        self.events: list[dict] = []
        self.db = self.FakeDB()
        self.job_id = str(uuid.UUID(int=3))
        patches = [
            mock.patch.object(tasks, "Session", lambda engine: self.db),
            mock.patch.object(tasks.lesson_image_db, "lesson_slots_sync", return_value=[self.group]),
            mock.patch.object(tasks, "publish_job_event", lambda db, jid, **f: self.events.append(f)),
            mock.patch.object(tasks.settings, "GEMINI_MODEL_IMAGE", "img-model"),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_task(self, generate, keys=None, force=False):
        with mock.patch.object(tasks.lesson_image, "generate_image", side_effect=generate):
            tasks.generate_lesson_images.run(self.job_id, 7, keys, force)
        return self.events[-1]

    def test_every_missing_picture_is_drawn_stored_and_reported(self):
        last = self.run_task(lambda prompt, kind: (b"webp-bytes", "image/webp"))
        self.assertEqual(last["status"], "succeeded")
        self.assertEqual(last["result"]["created"], 5)
        self.assertEqual(last["result"]["remaining"], 0)
        self.assertEqual(self.db.commits, 5)
        row = self.db.rows[self.slots[0].key]
        self.assertEqual((row.mime_type, row.model, row.kind, row.hidden), ("image/webp", "img-model", "vocab", False))
        self.assertEqual(row.prompt, self.slots[0].prompt)

    def test_a_picture_that_exists_is_left_alone(self):
        self.db = self.FakeDB(existing=[self.slots[0].key])
        calls = []
        last = self.run_task(lambda prompt, kind: calls.append(prompt) or (b"x", "image/webp"))
        self.assertEqual(len(calls), 4)
        self.assertEqual(last["result"]["created"], 4)

    def test_a_refused_scene_is_skipped_and_the_rest_still_drawn(self):
        def generate(prompt, kind):
            if "number 2" in prompt:
                raise lesson_image.ImageGenError("refused", blocked=True)
            return b"x", "image/webp"

        last = self.run_task(generate)
        self.assertEqual(last["status"], "succeeded")
        self.assertEqual(last["result"]["created"], 4)
        self.assertEqual([f["label"] for f in last["result"]["failed"]], ["w2"])
        self.assertEqual(last["result"]["remaining"], 1)

    def test_a_bad_key_ends_the_run_as_failed(self):
        def generate(prompt, kind):
            raise lesson_image.ImageGenError("Gemini refused the key", fatal=True)

        last = self.run_task(generate)
        self.assertEqual(last["status"], "failed")
        self.assertEqual(last["error"]["code"], "image_failed")
        self.assertIn("refused the key", last["error"]["message"])
        self.assertEqual(self.db.added, [])

    def test_drawing_again_replaces_the_picture_and_shows_it_again(self):
        key = self.slots[1].key
        self.db = self.FakeDB(existing=[key])
        self.db.rows[key].hidden = True
        self.run_task(lambda prompt, kind: (b"new", "image/webp"), keys=[key], force=True)
        row = self.db.rows[key]
        self.assertEqual(row.data, b"new")
        self.assertFalse(row.hidden)

    def test_progress_is_reported_as_pictures_are_finished(self):
        self.run_task(lambda prompt, kind: (b"x", "image/webp"))
        steps = [e.get("step") for e in self.events if e.get("status") == "running"]
        self.assertTrue(any("Đã vẽ 3/5" in s for s in steps if s))


if __name__ == "__main__":
    unittest.main()
