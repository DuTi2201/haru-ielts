"""Haru English lecture: English runs and Vietnamese runs are told apart word by word, the B1
notation is said as words, and the English runs are voiced by Azure (Chirp for Vietnamese)."""
import unittest
from types import SimpleNamespace
from unittest import mock

from app.core.config import settings
from app.services import azure_tts, google_tts, lecture_voice, lesson_audio as la, tts
from app.services.lecture_voice import KO, VI, split_runs


def pairs(text):
    return [(r.lang, r.text) for r in split_runs(text)]


class EnglishVietnameseSplitTests(unittest.TestCase):
    def test_a_word_line_is_the_english_word_then_the_vietnamese_meaning_with_a_gap(self):
        runs = split_runs("usually... thường thường.")
        self.assertEqual([(r.lang, r.text) for r in runs], [(KO, "usually..."), (VI, "thường thường.")])
        self.assertEqual(runs[0].pause_after_ms, lecture_voice.GAP_AFTER_ELLIPSIS_KO_MS)

    def test_whole_english_and_whole_vietnamese_lines(self):
        self.assertEqual(pairs("I go to school every day."), [(KO, "I go to school every day.")])
        self.assertEqual(pairs("Tôi hay đến lớp muộn."), [(VI, "Tôi hay đến lớp muộn.")])
        self.assertEqual(pairs("Bây giờ mình ôn lại. Nghe từng từ và nhắc lại."), [(VI, "Bây giờ mình ôn lại. Nghe từng từ và nhắc lại.")])

    def test_words_that_are_both_languages_follow_their_clause(self):
        self.assertEqual(pairs("So với Present simple."), [(VI, "So với"), (KO, "Present simple.")])
        self.assertEqual(
            pairs("Lỗi người Việt hay mắc: Quên be: không nói I studying, mà nói I am studying."),
            [(VI, "Lỗi người Việt hay mắc: Quên"), (KO, "be:"), (VI, "không nói"), (KO, "I studying,"), (VI, "mà nói"), (KO, "I am studying.")],
        )
        self.assertEqual(pairs("Phủ định. do not, does not cộng động từ."), [(VI, "Phủ định."), (KO, "do not, does not"), (VI, "cộng động từ.")])
        self.assertEqual(pairs("đang dở dang: I live in Hanoi"), [(VI, "đang dở dang:"), (KO, "I live in Hanoi")])

    def test_a_korean_script_keeps_the_hangul_split(self):
        self.assertEqual([r.lang for r in split_runs("Chào. 안녕하세요. Hello.")], [VI, KO, VI])


class B1NotationTests(unittest.TestCase):
    def test_patterns_are_said_as_words(self):
        self.assertEqual(la.speakable_pattern("Present simple: S + V(s/es)"), "Present simple: chủ ngữ cộng động từ thêm S hoặc ES")
        self.assertEqual(la.speakable_pattern("Present continuous: am/is/are + V-ing"), "Present continuous: am, is, are cộng động từ thêm ing")
        self.assertEqual(la.speakable_pattern("had + V3"), "had cộng quá khứ phân từ")
        self.assertEqual(la.speakable_pattern("Non-defining relative clauses: , who / , which"), "Non defining relative clauses: who, which")

    def test_a_struck_out_form_is_said_to_be_wrong(self):
        self.assertEqual(
            la.spoken_vi("quên `does`: ~~She work~~ → She works; ~~Does she works~~ → Does she work."),
            "quên does: không nói She work, mà nói She works; không nói Does she works, mà nói Does she work.",
        )
        self.assertEqual(
            la.spoken_vi("~~I am knowing~~, ~~I am wanting~~ → I know, I want."),
            "không nói I am knowing, I am wanting, mà nói I know, I want.",
        )

    def test_table_formula_keeps_plus_and_the_middle_dot(self):
        self.assertEqual(
            la.spoken_vi("I/you/we/they + V · he/she/it + V-s/es"),
            "I, you, we, they cộng động từ, he, she, it cộng động từ thêm S hoặc ES",
        )
        self.assertEqual(la.spoken_vi("quên `-s/-es`"), "quên đuôi S hoặc đuôi ES")

    def test_an_english_capital_a_is_not_an_adjective_and_a_sound_is_not_a_slash(self):
        self.assertEqual(la.spoken_vi("both A and B"), "both A and B")
        self.assertEqual(la.spoken_vi("đọc là /t/ hoặc /d/"), "đọc là âm t hoặc âm d")
        self.assertEqual(la.spoken_vi("think = cho rằng"), "think nghĩa là cho rằng")

    def test_the_sitting_number_is_said_once(self):
        lesson = SimpleNamespace(title="Unit 1 · Hiện tại đơn", title_en=None, notes=[], sessions=[{"title_vi": "Buổi 1 · Present simple", "vocab": ["x"], "grammar": []}])
        vocab = [SimpleNamespace(headword="x", meaning_vi="y", usage_note_vi=None, example_en=None, example_vi=None)]
        src, _v, _g = la.sitting_source(lesson, vocab, [], 1)
        self.assertEqual(src.title, "Unit 1 · Hiện tại đơn, buổi 1: Present simple")
        self.assertEqual(la.build_template_script(src).splitlines()[0], "Bài học Unit 1, Hiện tại đơn, buổi 1: Present simple.")


def _echo_pcm_file(pcm_file, size, rate):
    pcm_file.seek(0)
    return pcm_file.read(), b"", size // (rate * 2)


@mock.patch.object(tts.time, "sleep", lambda *_: None)
@mock.patch.object(tts, "transcode_pcm_file", _echo_pcm_file)
@mock.patch.object(tts, "_shared_slot", lambda gap: 0.0)
class AzureLectureTests(unittest.TestCase):
    def setUp(self):
        for p in (
            mock.patch.object(settings, "TTS_GG_CHIRP", "fake-test-credential"),
            mock.patch.object(settings, "TTS_CHIRP_VOICE", "en-GB-Chirp3-HD-Iapetus"),
            mock.patch.object(settings, "TTS_CHIRP_VOICE_VI", "vi-VN-Chirp3-HD-Iapetus"),
            mock.patch.object(settings, "TTS_LECTURE_WORKERS", 1),
            mock.patch.object(settings, "TTS_LECTURE_RPM", 0),
            mock.patch.object(settings, "AZURE_SPEECH_KEY", "fake-azure-key"),
            mock.patch.object(settings, "AZURE_SPEECH_REGION", "southeastasia"),
        ):
            p.start()
            self.addCleanup(p.stop)
        self.chirp, self.azure = [], []

    def fake_chirp(self, text, *, client=None, voice=None, rate=None):
        self.chirp.append((voice, text))
        return b"\x01\x00" * 10, 24000

    def fake_azure(self, text, voice="en-female-1"):
        self.azure.append((voice, text))
        return b"\x02\x00" * 10, 24000

    def test_english_goes_to_azure_and_vietnamese_to_chirp(self):
        with mock.patch.object(google_tts, "synthesize_pcm", self.fake_chirp), mock.patch.object(azure_tts, "synthesize_pcm", self.fake_azure):
            tts.synthesize_lecture_chirp("usually... thường thường.\nVí dụ.\nI usually have breakfast at seven...")
        self.assertEqual(self.azure, [("en-female-1", "usually."), ("en-female-1", "I usually have breakfast at seven.")])
        self.assertEqual([v for v, _t in self.chirp], ["vi-VN-Chirp3-HD-Iapetus", "vi-VN-Chirp3-HD-Iapetus"])

    def test_an_azure_failure_falls_back_to_chirp_for_that_phrase(self):
        def broken(text, voice="en-female-1"):
            raise azure_tts.AzureTTSError("Azure TTS HTTP 401")

        with mock.patch.object(google_tts, "synthesize_pcm", self.fake_chirp), mock.patch.object(azure_tts, "synthesize_pcm", broken):
            tts.synthesize_lecture_chirp("usually... thường thường.")
        self.assertEqual(self.chirp, [("en-GB-Chirp3-HD-Iapetus", "usually..."), ("vi-VN-Chirp3-HD-Iapetus", "thường thường.")])

    def test_the_cache_spec_names_the_azure_voice(self):
        self.assertTrue(tts.lecture_spec().endswith(azure_tts.spec()))
        with mock.patch.object(settings, "AZURE_SPEECH_KEY", ""):
            self.assertEqual(tts.lecture_spec(), google_tts.lecture_spec())


if __name__ == "__main__":
    unittest.main()
