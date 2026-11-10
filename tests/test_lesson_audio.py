"""Audio of a seeded lesson: the fixed (template) script, the parts Gemini writes a long
lesson in, the dialogue recordings of the practice set, and the voices they use."""
import hashlib
import json
import re
import unittest
from types import SimpleNamespace
from unittest import mock

from app.services import google_tts, ingestion, lecture_voice, lesson_audio as la, lesson_seed, podcast_script, tts

BUNDLE = lesson_seed.load_all()
# a review lesson has no words or cards of its own, so it has no lecture
LESSONS = [r for r in BUNDLE.lessons if r.seed.kind == "lesson"]
PILOT = LESSONS[0]


def source(resolved) -> la.LessonSource:
    s = resolved.seed
    return la.LessonSource(
        title=s.title,
        title_ko=s.title_ko,
        vocab=[la.VocabLine(v.hangul, v.meaning_vi, v.note_vi, v.example_ko, v.example_vi) for v in s.vocab],
        grammar=[
            la.GrammarLine(
                g.pattern, g.meaning_vi, g.usage_context_vi, g.note_vi, g.example_ko, g.example_vi,
                tuple((c.pattern, c.diff_vi) for c in g.contrasts),
            )
            for g in s.grammar
        ],
        notes=[(n.title, n.body) for n in s.notes],
        full_notes=tuple(i for i, n in enumerate(s.notes) if n.exam),
    )


class SpeakablePatternTests(unittest.TestCase):
    CASES = {
        "V + -고": "động từ cộng 고",
        "N(Thời gian) + 에": "danh từ chỉ thời gian cộng 에",
        "V + -아/어 놓다": "động từ cộng 아 hoặc 어 놓다",
        "V + -(으)ㄹ까요?": "động từ cộng 을까요",
        "V + -(으)ㅂ시다": "động từ cộng 읍시다",
        "A + -은/ㄴ": "tính từ cộng 은",
        "N + (으)로": "danh từ cộng 으로",
        "V + -는 데 걸리다/들다": "động từ cộng 는 데 걸리다 hoặc 들다",
        "N1(Thời gian)부터 N2(Thời gian)까지": "danh từ một chỉ thời gian 부터 danh từ hai chỉ thời gian 까지",
        "V + -(으)러 가다/오다": "động từ cộng 으러 가다 hoặc 오다",
        "V/A + -는데/은데/ㄴ데": "động từ hoặc tính từ cộng 는데 hoặc 은데",
        "Thể trần thuật (서술체: -(느)ㄴ다 / -다)": "Thể trần thuật, 서술체: 는다 hoặc 다",
    }

    def test_known_patterns(self):
        for written, spoken in self.CASES.items():
            self.assertEqual(la.speakable_pattern(written), spoken, written)

    def test_every_pattern_of_the_seed_can_be_read_aloud(self):
        for r in LESSONS:
            for g in r.seed.grammar:
                said = la.speakable_pattern(g.pattern)
                self.assertTrue(said, g.pattern)
                self.assertIsNone(re.search(r"[+()/~?]|[ㄱ-ㅎㅏ-ㅣ]|\b[VAN]\b", said), f"{g.pattern!r} -> {said!r}")


class SpokenVietnameseTests(unittest.TestCase):
    def test_markdown_slashes_and_marks(self):
        self.assertEqual(la.spoken_vi("**không dùng** `저 / 저는`"), "không dùng 저 hoặc 저는")
        self.assertEqual(la.spoken_vi("*오늘에 (X) → 오늘 (O)*"), "오늘에, sai, 오늘, đúng,".rstrip(","))
        self.assertEqual(la.spoken_vi("Ngày 1/10, trời nắng"), "Ngày 1 tháng 10, trời nắng")
        self.assertEqual(la.spoken_vi("Quá khứ (V/A)"), "Quá khứ, động từ hoặc tính từ")

    def test_optional_particles_and_endings(self):
        self.assertEqual(la.spoken_vi("Dạng kết hợp: 샤워(를) 하다 (Động từ)"), "Dạng kết hợp: 샤워 하다, Động từ")
        self.assertEqual(la.spoken_vi("hiện tại là `(이)다`"), "hiện tại là 이다")
        self.assertIn("니은", la.spoken_vi("đuôi `-ㄴ다`"))  # a bare jamo is read by its name

    def test_a_question_keeps_its_question_mark_but_a_repeat_line_trails_off(self):
        self.assertEqual(la._ko_line("먹을까요?", shadow=False), "먹을까요?")
        self.assertEqual(la._ko_line("먹어요.", shadow=False), "먹어요.")
        self.assertEqual(la._ko_line("먹을까요?", shadow=True), "먹을까요...")
        self.assertEqual(la._ko_line("배(가) 고프다", shadow=True), "배가 고프다...")

    def test_quotes_and_ellipses_are_dropped(self):
        self.assertEqual(la.spoken_vi('("làm... rồi...")'), "làm, rồi")


class TemplateScriptTests(unittest.TestCase):
    def test_the_same_lesson_gives_the_same_script(self):
        for r in LESSONS[:3]:
            self.assertEqual(la.build_template_script(source(r)), la.build_template_script(source(r)))

    def test_every_word_and_pattern_is_in_it(self):
        for r in LESSONS:
            script = la.build_template_script(source(r))
            for v in r.seed.vocab:
                self.assertIn(la._ko_line(v.hangul, shadow=True), script, v.hangul)
                self.assertNotIn("(", la._ko_line(v.hangul, shadow=True))
            for i, g in enumerate(r.seed.grammar, 1):
                self.assertIn(f"Mẫu số {i}.", script)
                self.assertIn(la.speakable_pattern(g.pattern), script)
            for n in r.seed.notes:
                self.assertIn("Phần ba. Lưu ý.", script)

    def test_the_words_are_repeated_for_review_with_the_same_text(self):
        script = la.build_template_script(source(PILOT))
        self.assertEqual(script.count("usually..."), 2)  # the voice reuses the recording of the repeat

    def test_nothing_in_it_trips_the_voice(self):
        for r in LESSONS:
            script = la.build_template_script(source(r))
            self.assertIsNone(re.search(r"[*#_`+=<>{}\[\]/→|~]", script), r.seed.slug)
            self.assertIsNone(re.search(r"[ㄱ-ㅎㅏ-ㅣ]", script), r.seed.slug)  # no bare jamo
            self.assertEqual(podcast_script.script_problems(script, la.MAX_SCRIPT_CHARS), [], r.seed.slug)

    def test_it_fits_in_one_recording_and_the_tail_is_voiced(self):
        for r in LESSONS:
            script = la.build_template_script(source(r))
            self.assertLess(len(script), la.MAX_SCRIPT_CHARS)
            plan = tts.plan_lecture(script, la.MAX_SCRIPT_CHARS)
            self.assertIn("Chúc bạn học tốt", plan[-1][1])

    def test_a_note_about_where_an_entry_came_from_is_not_read(self):
        src = la.LessonSource(
            "Thử", None, [la.VocabLine("밥", "Cơm", "Nghĩa chi tiết do biên tập bổ sung; tài liệu gốc chỉ ghi “Món”")], [], []
        )
        script = la.build_template_script(src)
        self.assertNotIn("biên tập", script)
        self.assertIn("밥...", script)

    LONG_NOTE = " ".join(f"Câu số {i} của ghi chú đời sống." for i in range(1, 41))  # ~1,300 characters

    def test_a_note_the_exam_course_needs_is_read_to_the_end_and_another_note_is_still_cut(self):
        src = la.LessonSource(
            "Thử", None, [la.VocabLine("밥", "Cơm")], [],
            [("Đời sống: bỏ rác", self.LONG_NOTE), ("Lưu ý thường", self.LONG_NOTE)], full_notes=(0,),
        )
        script = la.build_template_script(src)
        first, second = script.split("Lưu ý thường")
        self.assertIn("Câu số 40 của ghi chú đời sống.", first)
        self.assertNotIn("Câu số 40 của ghi chú đời sống.", second)
        self.assertIn("Câu số 1 của ghi chú đời sống.", second)

    def test_the_signature_of_a_lesson_without_such_notes_does_not_change(self):
        src = la.LessonSource("Thử", None, [la.VocabLine("밥", "Cơm")], [], [("Ghi chú", "Nội dung.")])
        self.assertEqual(la.source_signature(src), hashlib.sha256(repr(src).encode("utf-8")).hexdigest()[:24])

    def test_marking_a_note_as_read_in_full_gives_the_lesson_a_new_recording(self):
        notes = [("Đời sống", self.LONG_NOTE)]
        plain = la.LessonSource("Thử", None, [la.VocabLine("밥", "Cơm")], [], notes)
        marked = la.LessonSource("Thử", None, [la.VocabLine("밥", "Cơm")], [], notes, full_notes=(0,))
        self.assertNotEqual(la.source_signature(plain), la.source_signature(marked))

    def test_the_notes_of_a_lesson_row_carry_their_exam_tag_into_the_source(self):
        row = SimpleNamespace(
            title="Thử", title_ko=None,
            notes=[{"title": "A", "body": "x", "exam": "kiip-3"}, {"title": "B", "body": "y"}],
        )
        self.assertEqual(la.source_from_rows(row, [], []).full_notes, (0,))

    def test_a_korean_alternative_is_two_words_not_a_slash(self):
        src = la.LessonSource("Thử", None, [la.VocabLine("아침 / 점심", "Bữa sáng, bữa trưa")], [], [])
        self.assertIn("아침, 점심...", la.build_template_script(src))

    def test_vocab_pause_is_a_real_gap_for_repeating(self):
        src = la.LessonSource("Thử", None, [la.VocabLine("아침", "Bữa sáng")], [], [])
        runs = lecture_voice.split_runs(la.build_template_script(src))
        word = next(r for r in runs if r.text == "아침...")
        self.assertEqual(word.pause_after_ms, lecture_voice.GAP_AFTER_ELLIPSIS_KO_MS)


class ExtensionLectureTests(unittest.TestCase):
    """The 🟣 extension cards are part of the lecture, read the way they are meant to be heard."""

    def test_where_the_content_came_from_is_shown_not_read(self):
        for r in LESSONS:
            script = la.build_template_script(source(r))
            for word in ("Biên soạn", "tài liệu gốc", "🟣", "✗", "Kiến thức mở rộng ·"):
                self.assertNotIn(word, script, f"{r.seed.slug}: {word}")

    def test_a_wrong_form_is_said_to_be_wrong(self):
        self.assertEqual(
            la.spoken_vi("`*동생이 자야겠어요` ✗ → `동생은 자야 해요`"),
            "*동생이 자야겠어요, sai, nên nói 동생은 자야 해요",
        )
        self.assertEqual(la.spoken_vi("오늘에 ✗"), "오늘에, sai")
        self.assertEqual(la.spoken_vi("오늘 ✔"), "오늘, đúng")

    def test_only_how_it_is_built_and_when_it_is_used_are_read_from_the_usage(self):
        src = la.LessonSource(
            "Thử",
            None,
            [],
            [
                la.GrammarLine(
                    "V + -고",
                    "Rồi",
                    usage_vi=(
                        "🟣 **Kiến thức mở rộng** · ✍ **Dùng được**\n"
                        "**Cấu tạo:** V + -고\n"
                        "**Hoàn cảnh dùng:** nối hai việc\n"
                        "**Vì sao dễ nhầm:** nhầm với -아/어서\n"
                        "**Trong bài này:** bài 1"
                    ),
                )
            ],
            [],
        )
        script = la.build_template_script(src)
        self.assertIn("Cấu tạo. ", script)
        self.assertIn("Hoàn cảnh dùng. ", script)
        self.assertNotIn("Vì sao chọn", script)
        self.assertNotIn("Trong bài này", script)

    def test_a_contrast_names_the_pattern_it_is_compared_with(self):
        src = la.LessonSource(
            "Thử",
            None,
            [la.VocabLine("밥", "Cơm")],
            [la.GrammarLine("V + -고", "Rồi", contrasts=(("-(으)려고 하다", "Chỉ ý định trung tính."), ("-고", "`-고` nối hai việc.")))],
            [],
        )
        script = la.build_template_script(src)
        self.assertIn("So với", script)
        self.assertIn("Chỉ ý định trung tính.", script)
        self.assertEqual(script.count("So với"), 1)  # the one that opens with its own pattern says it itself


class SourceSignatureTests(unittest.TestCase):
    """A recording is kept while the lecture's source is the same: editing the exercises of a lesson
    does not record it again, editing a card does."""

    def test_exercises_do_not_change_it_but_cards_and_words_do(self):
        r = LESSONS[0]
        base = la.source_signature(source(r))
        self.assertEqual(base, la.source_signature(source(r)))
        edited_card = source(r)
        edited_card.grammar[0] = la.GrammarLine(
            edited_card.grammar[0].pattern, edited_card.grammar[0].meaning_vi + "!", edited_card.grammar[0].usage_vi
        )
        self.assertNotEqual(base, la.source_signature(edited_card))
        edited_word = source(r)
        edited_word.vocab[0] = la.VocabLine(edited_word.vocab[0].hangul, "khác")
        self.assertNotEqual(base, la.source_signature(edited_word))

    def test_every_lesson_has_its_own_signature(self):
        sigs = {la.source_signature(source(r)) for r in LESSONS}
        self.assertEqual(len(sigs), len(LESSONS))


class PlanPartsTests(unittest.TestCase):
    def check(self, v, g):
        parts = la.plan_parts(v, g)
        self.assertEqual(parts[0].vocab[0], 0)
        self.assertEqual(parts[-1].vocab[1], v)
        self.assertEqual(parts[-1].grammar[1], g)
        for a, b in zip(parts, parts[1:]):
            self.assertEqual((a.vocab[1], a.grammar[1]), (b.vocab[0], b.grammar[0]))  # no gap, no overlap
        for p in parts:
            self.assertLessEqual(p.vocab[1] - p.vocab[0], la.MAX_VOCAB_PER_PART)
            self.assertLessEqual(p.grammar[1] - p.grammar[0], la.MAX_GRAMMAR_PER_PART)
            self.assertEqual(p.total, len(parts))
        return parts

    def test_a_short_lesson_is_one_part(self):
        self.assertEqual(len(self.check(8, 1)), 1)
        self.assertEqual(len(self.check(12, 3)), 1)
        self.assertEqual(len(self.check(0, 0)), 1)

    def test_a_long_lesson_is_cut_evenly(self):
        parts = self.check(39, 3)
        self.assertEqual(len(parts), 4)
        sizes = [p.vocab[1] - p.vocab[0] for p in parts]
        self.assertLessEqual(max(sizes) - min(sizes), 1)

    def test_many_patterns_also_make_more_parts(self):
        self.assertEqual(len(self.check(5, 10)), 4)

    def test_every_seeded_lesson_is_covered(self):
        for r in LESSONS:
            self.check(len(r.seed.vocab), len(r.seed.grammar))


class PartPromptTests(unittest.TestCase):
    VOCAB = [("가다", "động từ", "đi", None, None, None)]

    def test_a_single_answer_prompt_is_the_one_articles_always_had(self):
        prompt = podcast_script.build_prompt("길", self.VOCAB, [])
        self.assertNotIn("PHẦN", prompt)
        self.assertIn("CẤU TRÚC (đây là thứ tự để bạn sắp bài", prompt)
        self.assertIn("A. Mở bài", prompt)
        self.assertIn("E. Kết bài", prompt)

    def test_the_first_part_opens_and_does_not_end_the_story(self):
        prompt = podcast_script.build_prompt("길", self.VOCAB, [], part=(1, 3))
        self.assertIn("PHẦN 1/3", prompt)
        self.assertIn("A. Mở bài", prompt)
        self.assertIn("CHƯA phải phần cuối", prompt)
        self.assertNotIn("E. Mang về nhà", prompt)

    def test_a_middle_part_continues_from_the_previous_outline(self):
        prompt = podcast_script.build_prompt("길", self.VOCAB, [], part=(2, 3), outline_so_far="Lan đang ở chợ")
        self.assertIn("Lan đang ở chợ", prompt)
        self.assertIn("không chào lại", prompt)
        self.assertNotIn("A. Mở bài", prompt)
        self.assertNotIn("E. Mang về nhà", prompt)

    def test_the_last_part_wraps_up_and_gets_the_notes(self):
        prompt = podcast_script.build_prompt("길", self.VOCAB, [], part=(3, 3), notes=["Lỗi hay gặp: nhầm 에"])
        self.assertIn("E. Mang về nhà", prompt)
        self.assertIn("<luu_y>", prompt)
        self.assertIn("nhầm 에", prompt)
        self.assertNotIn("<luu_y>", podcast_script.build_prompt("길", self.VOCAB, [], part=(1, 3), notes=["x"]))

    def test_the_editors_note_and_contrast_reach_the_writer(self):
        vocab = [("샤워", "danh từ", "tắm", None, None, None, "Dạng kết hợp: 샤워 하다")]
        grammar = [("V + -고", "rồi", None, "nối hành động", None, "khác -아/어서")]
        prompt = podcast_script.build_prompt("t", vocab, grammar)
        self.assertIn("Dạng kết hợp: 샤워 하다", prompt)
        self.assertIn("khác -아/어서", prompt)


class StoryGenerationTests(unittest.TestCase):
    def reply(self, n):
        script = f"Phần {n}. " + "Hôm nay Lan đi chợ mua trái cây và nói chuyện với bác bán hàng rất vui vẻ. " * 8
        return {"text": json.dumps({"outline": f"dàn ý phần {n}", "script": script}, ensure_ascii=False)}

    def lesson(self, n_vocab, n_grammar):
        return la.LessonSource(
            "Thử", None,
            [la.VocabLine(f"단어{i}", f"nghĩa {i}") for i in range(n_vocab)],
            [la.GrammarLine(f"V + -고{i}", "rồi") for i in range(n_grammar)],
            [("Lưu ý", "Đừng nhầm.")],
        )

    def test_a_long_lesson_is_written_in_parts_that_continue_each_other(self):
        replies = [self.reply(1), self.reply(2), self.reply(3)]
        seen = []
        with mock.patch.object(ingestion.gemini_client, "generate_structured", side_effect=replies) as g:
            script = ingestion.generate_lesson_story(self.lesson(30, 3), lambda d, t: seen.append((d, t)))
        self.assertEqual(g.call_count, 3)
        prompts = [c.kwargs["prompt"] for c in g.call_args_list]
        self.assertNotIn("dàn ý phần", prompts[0])
        self.assertIn("dàn ý phần 1", prompts[1])  # the next part is told where the story stopped
        self.assertIn("dàn ý phần 2", prompts[2])
        self.assertIn("PHẦN 3/3", prompts[2])
        self.assertEqual(g.call_args.kwargs["prompt_version"], la.STORY_VERSION)
        self.assertEqual([s.split(".")[0] for s in script.split("\n\n")], ["Phần 1", "Phần 2", "Phần 3"])
        self.assertEqual(seen[0], (0, 3))
        self.assertEqual(seen[-1], (3, 3))

    def test_each_part_gets_only_its_share_of_the_words(self):
        replies = [self.reply(1), self.reply(2), self.reply(3)]
        with mock.patch.object(ingestion.gemini_client, "generate_structured", side_effect=replies) as g:
            ingestion.generate_lesson_story(self.lesson(30, 0))
        prompts = [c.kwargs["prompt"] for c in g.call_args_list]
        for i, prompt in enumerate(prompts):
            mine = {f"단어{k}" for k in range(i * 10, i * 10 + 10)}
            for k in range(30):
                self.assertEqual(f"- 단어{k} " in prompt, f"단어{k}" in mine, (i, k))

    def test_a_short_lesson_is_one_answer_with_the_original_prompt(self):
        with mock.patch.object(ingestion.gemini_client, "generate_structured", return_value=self.reply(1)) as g:
            ingestion.generate_lesson_story(self.lesson(5, 1))
        self.assertEqual(g.call_count, 1)
        self.assertNotIn("PHẦN", g.call_args.kwargs["prompt"])


class DialogueTests(unittest.TestCase):
    LISTENING = {
        "id": "L1", "type": "listen_picture",
        "stimulus": {"kind": "audio", "turns": [{"speaker": "F", "text": "방은요?"}, {"speaker": "M", "text": "네."}]},
    }
    SPEAK = {"id": "S4", "type": "speak", "audio": {"kind": "audio", "turns": [{"speaker": "N", "text": "안내 방송입니다."}]}}

    def test_turns_come_from_a_listening_exercise_or_a_speaking_task(self):
        self.assertEqual(la.exercise_turns(self.LISTENING), [("F", "방은요?"), ("M", "네.")])
        self.assertEqual(la.exercise_turns(self.SPEAK), [("N", "안내 방송입니다.")])
        self.assertIsNone(la.exercise_turns({"id": "R1", "type": "read_cloze", "stimulus": {"kind": "cloze"}}))
        self.assertIsNone(la.exercise_turns({"id": "W1", "type": "write_essay"}))

    def test_every_listening_exercise_of_the_seed_has_turns(self):
        for ex in BUNDLE.exercises.values():
            if ex["skill"] == "listening":
                self.assertTrue(la.exercise_turns(ex), ex["id"])

    def test_the_key_follows_the_words_and_the_voices(self):
        turns = la.exercise_turns(self.LISTENING)
        key = la.dialogue_cache_key("L1", turns, "gc3dlg-a-b-r100")
        self.assertEqual(key, la.dialogue_cache_key("L1", list(turns), "gc3dlg-a-b-r100"))
        self.assertNotEqual(key, la.dialogue_cache_key("L1", [("F", "방은요?"), ("M", "아니요.")], "gc3dlg-a-b-r100"))
        self.assertNotEqual(key, la.dialogue_cache_key("L1", turns, "gc3dlg-a-c-r100"))
        self.assertLessEqual(len(key), 128)


class DialogueVoiceTests(unittest.TestCase):
    def pcm(self, ms=100):
        return (b"\x01\x00" * (24 * ms), 24000)

    def run_dialogue(self, turns, side_effect=None):
        calls = []

        def fake(text, *, voice=None, rate=None, client=None):
            calls.append((text, voice, rate))
            if side_effect:
                out = side_effect(text, voice)
                if out is not None:
                    return out
            return self.pcm()

        with mock.patch.object(google_tts, "is_configured", return_value=True), mock.patch.object(
            google_tts, "synthesize_pcm", side_effect=fake
        ), mock.patch.object(tts, "transcode_pcm", side_effect=lambda pcm, rate: (b"o", b"a", len(pcm) // (2 * rate) or 1)):
            tts.synthesize_dialogue_chirp(turns)
        return calls

    def test_each_speaker_gets_the_voice_and_the_natural_pace(self):
        with mock.patch.object(google_tts.settings, "TTS_CHIRP_VOICE_FEMALE", "ko-KR-Chirp3-HD-Aoede"), mock.patch.object(
            google_tts.settings, "TTS_CHIRP_VOICE", "ko-KR-Chirp3-HD-Iapetus"
        ), mock.patch.object(google_tts.settings, "TTS_CHIRP_SPEAKING_RATE_EXAM", 1.0):
            calls = self.run_dialogue([("F", "안녕하세요."), ("M", "네."), ("N", "끝.")])
        self.assertEqual([c[1] for c in calls], ["ko-KR-Chirp3-HD-Aoede", "ko-KR-Chirp3-HD-Iapetus", "ko-KR-Chirp3-HD-Iapetus"])
        self.assertTrue(all(c[2] == 1.0 for c in calls))  # not the 0.85 shadowing pace

    def test_a_refused_female_voice_is_replaced_by_one_google_lists(self):
        def refuse(text, voice):
            if voice == "en-GB-Chirp3-HD-Aoede":
                raise google_tts.GoogleTTSError("voice does not exist")

        with mock.patch.object(google_tts, "pick_ko_voice", return_value="en-GB-Chirp3-HD-Kore") as pick:
            calls = self.run_dialogue([("F", "One."), ("F", "Two.")], refuse)
        pick.assert_called_once_with("en-GB-Chirp3-HD-Aoede", "FEMALE")
        self.assertEqual([c[1] for c in calls][-1], "en-GB-Chirp3-HD-Kore")  # the rest of the dialogue keeps it

    def test_without_the_credential_it_does_not_try(self):
        with mock.patch.object(google_tts, "is_configured", return_value=False):
            with self.assertRaises(RuntimeError):
                tts.synthesize_dialogue_chirp([("F", "안녕.")])

    def test_the_spec_changes_with_either_voice_or_the_pace(self):
        base = google_tts.dialogue_spec()
        with mock.patch.object(google_tts.settings, "TTS_CHIRP_VOICE_FEMALE", "ko-KR-Chirp3-HD-Kore"):
            self.assertNotEqual(google_tts.dialogue_spec(), base)
        with mock.patch.object(google_tts.settings, "TTS_CHIRP_SPEAKING_RATE_EXAM", 0.9):
            self.assertNotEqual(google_tts.dialogue_spec(), base)


class AzureDialogueTests(unittest.TestCase):
    """The practice dialogue in Azure's two voices, with Chirp only as the fallback."""

    def run_dialogue(self, turns):
        calls = []

        def fake(text, voice="ko-female-1"):
            calls.append((text, voice))
            return (b"\x01\x00" * 2400, 24000)

        with mock.patch.object(tts.azure_tts, "is_configured", return_value=True), mock.patch.object(
            tts.azure_tts, "synthesize_pcm", side_effect=fake
        ), mock.patch.object(tts, "transcode_pcm", side_effect=lambda pcm, rate: (b"o", b"a", 1)):
            tts.synthesize_dialogue_azure(turns)
        return calls

    def test_each_speaker_gets_a_voice_of_its_own(self):
        calls = self.run_dialogue([("F", "안녕하세요."), ("M", "네."), ("N", "끝.")])
        self.assertEqual([c[1] for c in calls], ["ko-female-1", "ko-male-1", "ko-male-1"])

    def test_without_azure_it_does_not_try(self):
        with mock.patch.object(tts.azure_tts, "is_configured", return_value=False):
            with self.assertRaises(RuntimeError):
                tts.synthesize_dialogue_azure([("F", "안녕.")])

    def test_the_spec_names_both_voices_and_the_pace(self):
        base = tts.azure_tts.dialogue_spec()
        with mock.patch.object(tts.azure_tts.settings, "AZURE_TTS_VOICE_MALE", "ko-KR-GookMinNeural"):
            self.assertNotEqual(tts.azure_tts.dialogue_spec(), base)
        with mock.patch.object(tts.azure_tts.settings, "AZURE_TTS_RATE", 0.8):
            self.assertNotEqual(tts.azure_tts.dialogue_spec(), base)

    def test_azure_failing_falls_back_to_chirp_under_the_fallback_key(self):
        from app.workers import tasks

        db = mock.MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = None
        with mock.patch.object(tasks.azure_tts, "is_configured", return_value=True), mock.patch.object(
            tasks.tts, "synthesize_dialogue_azure", side_effect=RuntimeError("azure down")
        ), mock.patch.object(tasks.tts, "chirp_enabled", return_value=True), mock.patch.object(
            tasks.tts, "synthesize_dialogue_chirp", return_value=(b"o", b"a", 3)
        ):
            reuse, _o, _a, dur, key = tasks._voice_dialogue(db, [("F", "안녕.")], "az-key", "chirp-key", None, "gem-key")
        self.assertIsNone(reuse)
        self.assertEqual((dur, key), (3, "chirp-key"))  # not under the Azure key: Azure is tried again next play

    def test_azure_working_files_under_its_own_key(self):
        from app.workers import tasks

        db = mock.MagicMock()
        with mock.patch.object(tasks.azure_tts, "is_configured", return_value=True), mock.patch.object(
            tasks.tts, "synthesize_dialogue_azure", return_value=(b"o", b"a", 5)
        ):
            _r, _o, _a, dur, key = tasks._voice_dialogue(db, [("F", "안녕.")], "az-key", "chirp-key", None, "gem-key")
        self.assertEqual((dur, key), (5, "az-key"))


class LongScriptTests(unittest.TestCase):
    def test_a_longer_limit_voices_what_the_default_cuts(self):
        text = "Xin chào các bạn. 안녕하세요... " * 600
        self.assertLess(len("".join(t for _l, t, _p in tts.plan_lecture(text))), len(text))
        self.assertEqual(
            len(tts.plan_lecture(text, la.MAX_SCRIPT_CHARS)),
            len(lecture_voice.split_runs(text)),
        )


if __name__ == "__main__":
    unittest.main()


def test_spoken_body_reads_table_rows_as_label_and_content_without_the_header():
    from app.services.lesson_audio import _spoken_body

    body = (
        "Bỏ `ㅅ` trước nguyên âm.\n"
        "| Đuôi | Xử lý | Ví dụ |\n"
        "|---|---|---|\n"
        "| **NGUYÊN ÂM** — `-아/어`, `-(으)면` | **BỎ** `ㅅ` | `나아요`, `나으면` |\n"
        "| **PHỤ ÂM** — `-고` | **GIỮ** `ㅅ` | `낫고` |\n"
        "- `낫다` → `나아요`"
    )
    assert _spoken_body(body).splitlines() == [
        "Bỏ `ㅅ` trước nguyên âm.",
        "**nguyên âm**. **bỏ** `ㅅ`. `나아요`, `나으면`.",
        "**phụ âm**. **giữ** `ㅅ`. `낫고`.",
        "`낫다` → `나아요`",
    ]


def test_spoken_body_does_not_double_the_punctuation_of_question_and_answer_cells():
    from app.services.lesson_audio import _spoken_body

    body = "| Hỏi về | Câu hỏi | Trả lời |\n| **Giờ** | `몇 시예요?` | `세 시예요.` |"
    assert _spoken_body(body) == "**Giờ**. `몇 시예요?` `세 시예요.`"


def test_spoken_body_leaves_the_old_bullet_character_alone():
    from app.services.lesson_audio import _is_screen_layout, _spoken_body

    body = "gồm 2 cụm:\n• `A에 비해`: so với A"
    assert _spoken_body(body) == body
    assert not _is_screen_layout(body)
    assert _is_screen_layout("a\n- b") and _is_screen_layout("a\n| b | c |")


def test_spoken_usage_of_a_table_and_word_list_card_keeps_every_form():
    from app.services.lesson_audio import GrammarLine, _spoken_usage

    usage = (
        "**Cấu tạo:** Bỏ `ㄷ` thành `ㄹ` trước nguyên âm.\n"
        "| Đuôi | Xử lý | Ví dụ |\n"
        "| **NGUYÊN ÂM** — `-아/어` | **ĐỔI** | `들어요`, `들으면` |\n"
        "| **PHỤ ÂM** — `-고` | **GIỮ** | `듣고` |\n"
        + "\n".join(f"- `단어{i}` (nghĩa) → `형태{i}`" for i in range(12))
        + "\n**Hoàn cảnh dùng:** Nghe nhạc: `음악을 들어요`."
    )
    out = _spoken_usage(GrammarLine(pattern="ㄷ", meaning_vi="x", usage_vi=usage))
    assert len(out) == 2
    form = out[0]
    for token in ("들어요", "들으면", "듣고", "nguyên âm", "phụ âm", "형태11"):
        assert token in form, token
    assert "|" not in form and "**" not in form and "`" not in form
    assert out[1].startswith("Hoàn cảnh dùng.")
