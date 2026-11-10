"""Reusing an existing word picture instead of drawing a new one: how a missing picture is
matched with existing ones (pure), and the Studio endpoints that list the matches and copy
a picture (database and job state replaced)."""
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.routers import lesson_images
from app.models import SceneImage
from app.schemas import ImageReuseRequest, ImageReuseSuggestedRequest
from app.services import image_reuse, lesson_image, lesson_image_db, lesson_seed

NOW = datetime(2026, 10, 6, 2, 0, tzinfo=timezone.utc)
EDITOR = SimpleNamespace(id=uuid.UUID(int=9), role="editor")
BUNDLE = lesson_seed.load_all()


def word(hangul, meaning, prompt=None, kind="vocab"):
    return lesson_image.Slot(kind=kind, label=hangul, prompt=prompt or f"A drawing of {hangul} on a plain background.", meaning=meaning)


def group(lesson_id, *slots):
    return lesson_image_db.LessonSlots(lesson_id=lesson_id, slug=f"s{lesson_id}", title=f"L{lesson_id}", slots=list(slots))


def stored_of(*slots, hidden=()):
    return {s.key: SimpleNamespace(cache_key=s.key, hidden=s.key in hidden, created_at=NOW, model="m") for s in slots}


class SenseTests(unittest.TestCase):
    def test_a_gloss_is_split_into_its_meanings(self):
        self.assertEqual(image_reuse.senses("Buổi sáng / Bữa sáng"), {"buổi sáng", "bữa sáng"})
        self.assertEqual(image_reuse.senses("Thức dậy; dậy, (sớm)"), {"thức dậy", "dậy", "sớm"})

    def test_leading_sự_việc_cái_con_do_not_matter(self):
        self.assertEqual(image_reuse.senses("Sự thức dậy"), image_reuse.senses("thức dậy"))
        self.assertEqual(image_reuse.senses("Cái bàn"), {"bàn"})
        self.assertEqual(image_reuse.senses("Việc nhà"), {"nhà"})

    def test_nothing_in_nothing_out(self):
        self.assertEqual(image_reuse.senses(None), frozenset())
        self.assertEqual(image_reuse.senses("  / ; "), frozenset())

    def test_a_verb_shares_the_stem_of_its_noun(self):
        self.assertEqual(image_reuse.stem("샤워하다"), "샤워")
        self.assertEqual(image_reuse.stem("완성되다"), "완성")
        self.assertEqual(image_reuse.stem("샤워"), "샤워")
        self.assertEqual(image_reuse.stem("하다"), "하다")  # nothing left of it otherwise


class SuggestTests(unittest.TestCase):
    def test_a_noun_and_its_verb_of_the_same_meaning_are_a_sure_match(self):
        noun = word("샤워", "Sự tắm vòi hoa sen")
        verb = word("샤워하다", "Tắm vòi hoa sen")
        found = image_reuse.suggest([group(1, noun, verb)], stored_of(noun))
        self.assertEqual(list(found), [verb.key])
        top = found[verb.key][0]
        self.assertEqual((top.key, top.label, top.confident), (noun.key, "샤워", True))
        self.assertIn("샤워", top.why)

    def test_two_words_with_exactly_the_same_meanings_are_a_sure_match(self):
        a = word("일어나다", "Thức dậy")
        b = word("기상", "Sự thức dậy")
        found = image_reuse.suggest([group(1, a), group(2, b)], stored_of(a))
        self.assertTrue(found[b.key][0].confident)
        self.assertIn("Cùng nghĩa", found[b.key][0].why)

    def test_a_partly_shared_meaning_is_only_suggested(self):
        a = word("양말", "Tất")
        b = word("신다", "Đi giày / Tất / Mang")
        found = image_reuse.suggest([group(1, a, b)], stored_of(a))
        top = found[b.key][0]
        self.assertEqual(top.key, a.key)
        self.assertFalse(top.confident)

    def test_the_same_stem_alone_is_suggested_not_sure(self):
        a = word("일", "Công việc")
        b = word("일하다", "Làm việc")
        found = image_reuse.suggest([group(1, a, b)], stored_of(a))
        self.assertFalse(found[b.key][0].confident)

    def test_unrelated_words_are_not_matched(self):
        a = word("학교", "Trường học")
        b = word("사과", "Quả táo")
        self.assertEqual(image_reuse.suggest([group(1, a, b)], stored_of(a)), {})

    def test_a_word_that_has_a_picture_needs_no_suggestion(self):
        a, b = word("샤워", "Tắm"), word("샤워하다", "Tắm")
        self.assertEqual(image_reuse.suggest([group(1, a, b)], stored_of(a, b)), {})

    def test_a_hidden_picture_is_never_offered(self):
        a, b = word("샤워", "Tắm"), word("샤워하다", "Tắm")
        self.assertEqual(image_reuse.suggest([group(1, a, b)], stored_of(a, hidden={a.key})), {})

    def test_only_word_pictures_are_matched(self):
        banner = lesson_image.Slot(kind="lesson", label="Ảnh đầu bài", prompt="A banner of a morning.", meaning="Buổi sáng")
        scene = lesson_image.Slot(kind="scene", label="Buổi sáng", prompt="A scene of a morning.", meaning="Buổi sáng")
        target = word("아침", "Buổi sáng")
        self.assertEqual(image_reuse.suggest([group(1, banner, scene, target)], stored_of(banner, scene)), {})

    def test_the_best_candidates_come_first_at_most_three(self):
        target = word("공부하다", "Học")
        sure = word("공부", "Sự học")
        others = [word(f"w{i}", "Học / thứ khác") for i in range(4)]
        found = image_reuse.suggest([group(1, target, sure, *others)], stored_of(sure, *others))
        keys = [c.key for c in found[target.key]]
        self.assertEqual(keys[0], sure.key)
        self.assertEqual(len(keys), image_reuse.MAX_CANDIDATES)

    def test_a_picture_is_not_offered_to_itself(self):
        a = word("샤워", "Tắm")
        self.assertEqual(image_reuse.suggest([group(1, a, a)], stored_of()), {})

    def test_the_real_lessons_can_all_be_matched_without_error(self):
        groups = []
        for i, r in enumerate(BUNDLE.lessons, start=1):
            meanings = {v.hangul: v.meaning_vi for v in r.seed.vocab}
            groups.append(
                group(
                    i,
                    *lesson_image.lesson_slots(
                        r.seed.slug, [v.hangul for v in r.seed.vocab], [g.pattern for g in r.seed.grammar], r.practice, meanings
                    ),
                )
            )
        slots = [s for g in groups for s in g.slots]
        self.assertTrue(any(s.kind == "vocab" and s.meaning for s in slots))
        self.assertEqual(image_reuse.suggest(groups, {}), {})  # nothing exists, nothing to reuse
        # every picture exists except one word: whatever is offered for it is a real, other picture
        vocab = [s for s in slots if s.kind == "vocab"]
        missing = vocab[0]
        found = image_reuse.suggest(groups, stored_of(*[s for s in slots if s.key != missing.key]))
        for candidate in found.get(missing.key, []):
            self.assertNotEqual(candidate.key, missing.key)


class LessonSlotMeaningTests(unittest.TestCase):
    def test_a_word_slot_carries_its_meaning_but_it_does_not_change_which_picture_it_is(self):
        plan_word = next(iter(lesson_image.load_plan().vocab))
        with_meaning = lesson_image.lesson_slots(None, [plan_word], [], None, {plan_word: "Nghĩa"})
        without = lesson_image.lesson_slots(None, [plan_word], [], None)
        self.assertEqual(with_meaning[0].meaning, "Nghĩa")
        self.assertIsNone(without[0].meaning)
        self.assertEqual(with_meaning, without)
        self.assertEqual(with_meaning[0].key, without[0].key)


# ----------------------------------------------------------------- endpoints --
class ReuseEndpointBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.noun = word("샤워", "Sự tắm vòi hoa sen")
        self.verb = word("샤워하다", "Tắm vòi hoa sen")
        self.other = word("학교", "Trường học")
        self.groups = [group(7, self.noun, self.verb, self.other)]
        for p in (
            mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", True),
            mock.patch.object(lesson_image.settings, "GEMINI_MODEL_IMAGE", "img-model"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def world(self, stored, active=None, groups=None):
        patches = [
            mock.patch.object(lesson_image_db, "lesson_slots_async", mock.AsyncMock(return_value=groups or self.groups)),
            mock.patch.object(lesson_images, "_stored", mock.AsyncMock(return_value=stored)),
            mock.patch.object(lesson_images, "_active_job", mock.AsyncMock(return_value=active)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def picture(self, slot, hidden=False, model="gemini-x"):
        return SceneImage(
            cache_key=slot.key, mime_type="image/webp", data=b"webp-bytes", prompt=slot.prompt, model=model,
            hidden=hidden, kind="vocab",
        )

    def db(self, rows=None, commit_error=None):
        """`rows`: key -> SceneImage that exist."""
        rows = rows or {}
        db = mock.MagicMock()
        db.get = mock.AsyncMock(side_effect=lambda model, key: rows.get(key))
        db.add = mock.MagicMock()
        db.commit = mock.AsyncMock(side_effect=commit_error)
        db.rollback = mock.AsyncMock()

        async def refresh(row):
            row.created_at = NOW

        db.refresh = mock.AsyncMock(side_effect=refresh)
        result = mock.MagicMock()
        result.scalars.return_value.all.return_value = list(rows.values())
        db.execute = mock.AsyncMock(return_value=result)
        return db


class OverviewAndLessonTests(ReuseEndpointBase):
    async def test_the_overview_counts_what_could_be_reused(self):
        self.world(stored={self.noun.key: SimpleNamespace(hidden=False, created_at=NOW, model="m")})
        out = await lesson_images.images_overview(mock.MagicMock(), EDITOR)
        self.assertEqual((out.reusable, out.reusable_sure), (1, 1))
        self.assertEqual(out.lessons[0].reusable, 1)

    async def test_a_missing_word_lists_the_pictures_it_could_take(self):
        self.world(stored={self.noun.key: SimpleNamespace(hidden=False, created_at=NOW, model="m")})
        out = await lesson_images.lesson_images(7, mock.MagicMock(), EDITOR)
        by_key = {s.key: s for s in out.slots}
        gap = by_key[self.verb.key]
        self.assertEqual(gap.meaning, "Tắm vòi hoa sen")
        self.assertEqual([c.key for c in gap.reuse], [self.noun.key])
        self.assertTrue(gap.reuse[0].confident)
        self.assertIn(f"/scene-image/{self.noun.key}?v=", gap.reuse[0].url)
        self.assertEqual(by_key[self.noun.key].reuse, [])  # it has a picture
        self.assertEqual(by_key[self.other.key].reuse, [])  # nothing like it


class ReuseOneTests(ReuseEndpointBase):
    async def test_the_picture_is_copied_under_the_words_key(self):
        self.world(stored={})
        origin = self.picture(self.noun)
        db = self.db({self.noun.key: origin})
        out = await lesson_images.reuse_image(
            ImageReuseRequest(from_key=self.noun.key, to_key=self.verb.key), db, EDITOR
        )
        copy = db.add.call_args.args[0]
        self.assertEqual(copy.cache_key, self.verb.key)
        self.assertEqual(copy.data, b"webp-bytes")
        self.assertEqual(copy.prompt, self.verb.prompt)  # the word's own prompt, so it is that word's picture
        self.assertEqual((copy.kind, copy.hidden), ("vocab", False))
        self.assertEqual(copy.model, "reuse:gemini-x")
        self.assertEqual(out.label, "샤워하다")
        self.assertIn(self.verb.key, out.url)
        db.commit.assert_awaited_once()

    async def test_nothing_is_copied_while_a_run_is_drawing(self):
        self.world(stored={}, active=SimpleNamespace(id=uuid.UUID(int=5)))
        with self.assertRaises(HTTPException) as caught:
            await lesson_images.reuse_image(
                ImageReuseRequest(from_key=self.noun.key, to_key=self.verb.key), self.db(), EDITOR
            )
        self.assertEqual(caught.exception.status_code, 409)

    async def test_a_word_that_already_has_a_picture_keeps_it(self):
        self.world(stored={})
        db = self.db({self.noun.key: self.picture(self.noun), self.verb.key: self.picture(self.verb)})
        with self.assertRaises(HTTPException) as caught:
            await lesson_images.reuse_image(ImageReuseRequest(from_key=self.noun.key, to_key=self.verb.key), db, EDITOR)
        self.assertEqual(caught.exception.status_code, 409)
        db.add.assert_not_called()

    async def test_a_hidden_or_missing_source_is_refused(self):
        self.world(stored={})
        for rows in ({}, {self.noun.key: self.picture(self.noun, hidden=True)}):
            db = self.db(rows)
            with self.assertRaises(HTTPException) as caught:
                await lesson_images.reuse_image(
                    ImageReuseRequest(from_key=self.noun.key, to_key=self.verb.key), db, EDITOR
                )
            self.assertEqual(caught.exception.status_code, 409)
            db.add.assert_not_called()

    async def test_only_known_word_pictures_can_be_used(self):
        banner = lesson_image.Slot(kind="lesson", label="Ảnh đầu bài", prompt="A banner of a morning in the city.")
        self.world(stored={}, groups=[group(7, self.noun, self.verb, banner)])
        db = self.db({self.noun.key: self.picture(self.noun)})
        cases = [
            (self.noun.key, "not-a-key"),  # target is no word's picture
            ("not-a-key", self.verb.key),  # source is not either
            (self.noun.key, banner.key),  # a banner is not a word
            (banner.key, self.verb.key),
        ]
        for origin, target in cases:
            with self.assertRaises(HTTPException) as caught:
                await lesson_images.reuse_image(ImageReuseRequest(from_key=origin, to_key=target), db, EDITOR)
            self.assertEqual(caught.exception.status_code, 404, (origin, target))
        with self.assertRaises(HTTPException) as caught:
            await lesson_images.reuse_image(ImageReuseRequest(from_key=self.noun.key, to_key=self.noun.key), db, EDITOR)
        self.assertEqual(caught.exception.status_code, 400)
        db.add.assert_not_called()

    async def test_two_editors_at_once_get_a_clean_409(self):
        self.world(stored={})
        db = self.db({self.noun.key: self.picture(self.noun)}, commit_error=IntegrityError("i", {}, Exception("dup")))
        with self.assertRaises(HTTPException) as caught:
            await lesson_images.reuse_image(ImageReuseRequest(from_key=self.noun.key, to_key=self.verb.key), db, EDITOR)
        self.assertEqual(caught.exception.status_code, 409)
        db.rollback.assert_awaited_once()


class ReuseSuggestedTests(ReuseEndpointBase):
    def stored(self, *slots):
        return {s.key: SimpleNamespace(hidden=False, created_at=NOW, model="m") for s in slots}

    async def test_every_sure_match_is_filled_and_nothing_else(self):
        doubtful_a, doubtful_b = word("일", "Công việc"), word("일하다", "Làm việc")
        self.world(
            stored=self.stored(self.noun, doubtful_a),
            groups=[group(7, self.noun, self.verb, self.other, doubtful_a, doubtful_b)],
        )
        db = self.db({self.noun.key: self.picture(self.noun), doubtful_a.key: self.picture(doubtful_a)})
        out = await lesson_images.reuse_suggested(ImageReuseSuggestedRequest(), db, EDITOR)
        self.assertEqual(out.reused, 1)
        self.assertEqual((out.items[0].to_key, out.items[0].from_key), (self.verb.key, self.noun.key))
        self.assertEqual(db.add.call_count, 1)
        db.commit.assert_awaited_once()

    async def test_a_lesson_can_be_asked_alone(self):
        far = word("공부", "Sự học")
        near = word("공부하다", "Học")
        self.world(
            stored=self.stored(self.noun, far),
            groups=[group(7, self.noun, self.verb), group(8, far, near)],
        )
        db = self.db({self.noun.key: self.picture(self.noun), far.key: self.picture(far)})
        out = await lesson_images.reuse_suggested(ImageReuseSuggestedRequest(lesson_id=8), db, EDITOR)
        self.assertEqual([i.to_key for i in out.items], [near.key])

    async def test_nothing_sure_means_nothing_done(self):
        self.world(stored=self.stored(self.other))
        db = self.db({self.other.key: self.picture(self.other)})
        out = await lesson_images.reuse_suggested(ImageReuseSuggestedRequest(), db, EDITOR)
        self.assertEqual((out.reused, out.items), (0, []))
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_an_unknown_lesson_is_404_and_a_running_draw_is_409(self):
        self.world(stored={})
        with self.assertRaises(HTTPException) as caught:
            await lesson_images.reuse_suggested(ImageReuseSuggestedRequest(lesson_id=99), self.db(), EDITOR)
        self.assertEqual(caught.exception.status_code, 404)
        self.world(stored={}, active=SimpleNamespace(id=uuid.UUID(int=5)))
        with self.assertRaises(HTTPException) as caught:
            await lesson_images.reuse_suggested(ImageReuseSuggestedRequest(), self.db(), EDITOR)
        self.assertEqual(caught.exception.status_code, 409)


class WhatTheLearnersSeeTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_copied_picture_is_a_normal_picture_of_the_word(self):
        """The copy is filed under key(prompt of the word), which is exactly what the lesson
        endpoints look up — so nothing else has to change for learners to see it."""
        slot = word("샤워하다", "Tắm")
        db = mock.MagicMock()
        result = mock.MagicMock()
        result.all.return_value = [(slot.key, NOW)]
        db.execute = mock.AsyncMock(return_value=result)
        with mock.patch.object(lesson_image.settings, "LESSON_IMAGE_GEN_ENABLED", True), mock.patch.object(
            lesson_image.settings, "GEMINI_MODEL_IMAGE", "img-model"
        ):
            urls = await lesson_image_db.visible_urls(db, [slot.prompt])
        self.assertEqual(list(urls), [slot.prompt])
        self.assertIn(slot.key, urls[slot.prompt])


if __name__ == "__main__":
    unittest.main()
