"""The Korean voice: NIKL pronunciation before speech (korean_g2p) and Azure as the voice for
short Korean texts when configured (azure_tts, tts.synthesize_korean_with_provider)."""
import unittest
from unittest import mock

from app.services import azure_tts, korean_g2p, text_audio, tts


class G2PTests(unittest.TestCase):
    def test_standalone_words_are_said_as_pronounced(self):
        for written, said in [("학생", "학쌩"), ("한국어", "한구거"), ("같이", "가치"), ("국물", "궁물"), ("신라", "실라"), ("좋다", "조타")]:
            self.assertEqual(korean_g2p.pronounce(written), said)

    def test_a_word_with_a_particle_is_left_to_the_voice(self):
        body = korean_g2p.to_ssml_body("학생이 와요. 학생")
        self.assertIn("학생이", body)
        self.assertEqual(body.count("<sub"), 1)
        self.assertIn('<sub alias="학쌩">학생</sub>', body)

    def test_text_is_escaped(self):
        self.assertNotIn("<b>", korean_g2p.to_ssml_body("<b>안녕</b>"))


class AzureTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch.multiple(azure_tts.settings, AZURE_SPEECH_KEY="k", AZURE_SPEECH_REGION="koreacentral")
        p.start()
        self.addCleanup(p.stop)

    def test_voices_and_spec(self):
        self.assertEqual(azure_tts.voice_for("ko-female-2"), "ko-KR-SunHiNeural")
        self.assertEqual(azure_tts.voice_for("ko-male-1"), "ko-KR-InJoonNeural")
        self.assertTrue(azure_tts.spec().startswith("az-sunhi-"))

    def test_ssml_carries_the_pronunciation(self):
        x = azure_tts.ssml("학생", "ko-female-1")
        self.assertIn('xml:lang="ko-KR"', x)
        self.assertIn('<sub alias="학쌩">학생</sub>', x)

    def test_azure_is_first_and_chirp_is_the_fallback(self):
        with mock.patch.object(azure_tts, "synthesize_pcm", return_value=(b"\0\0" * 2400, 24000)), \
             mock.patch.object(tts, "transcode_pcm", return_value=(b"o", b"a", 1)):
            self.assertEqual(tts.synthesize_korean_with_provider("학생")[3], "azure")
        with mock.patch.object(azure_tts, "synthesize_pcm", side_effect=azure_tts.AzureTTSError("x")), \
             mock.patch.object(tts.google_tts, "is_configured", return_value=True), \
             mock.patch.object(tts, "_synthesize_korean_chirp", return_value=(b"o", b"a", 1)):
            self.assertEqual(tts.synthesize_korean_with_provider("학생")[3], "chirp")

    def test_the_cache_key_follows_the_voice(self):
        with_azure = text_audio.cache_key("학생", "ko-female-1")
        with mock.patch.multiple(azure_tts.settings, AZURE_SPEECH_KEY=""):
            self.assertNotEqual(with_azure, text_audio.cache_key("학생", "ko-female-1"))

    def test_a_chirp_recording_is_replaced_once_azure_is_on(self):
        row = mock.MagicMock(provider="chirp")
        self.assertFalse(text_audio.is_usable(row))
        row.provider = "azure"
        self.assertTrue(text_audio.is_usable(row))


if __name__ == "__main__":
    unittest.main()
