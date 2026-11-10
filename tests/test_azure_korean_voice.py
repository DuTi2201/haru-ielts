"""Azure Neural voice for short English/Korean texts when configured (azure_tts, tts.synthesize_korean_with_provider)."""
import unittest
from unittest import mock

from app.services import azure_tts, text_audio, tts


class AzureTests(unittest.TestCase):
    def setUp(self):
        p = mock.patch.multiple(azure_tts.settings, AZURE_SPEECH_KEY="k", AZURE_SPEECH_REGION="koreacentral")
        p.start()
        self.addCleanup(p.stop)

    def test_voices_and_spec(self):
        self.assertEqual(azure_tts.voice_for("en-female-1"), "en-GB-SoniaNeural")
        self.assertEqual(azure_tts.voice_for("en-male-1"), "en-GB-RyanNeural")
        self.assertEqual(azure_tts.voice_for("ko-female-2"), "en-GB-SoniaNeural")
        self.assertEqual(azure_tts.voice_for("ko-male-1"), "en-GB-RyanNeural")
        self.assertTrue(azure_tts.spec().startswith("az-sonia-"))

    def test_ssml_skips_korean_g2p_for_english_voices(self):
        x = azure_tts.ssml("<b>usually</b>", "en-female-1")
        self.assertIn('xml:lang="en-GB"', x)
        self.assertNotIn("<sub", x)
        self.assertNotIn("<b>", x)
        self.assertIn("usually", x)
        with mock.patch.multiple(azure_tts.settings, AZURE_TTS_VOICE="en-US-JennyNeural"):
            us = azure_tts.ssml("schedule", "en-female-1")
            self.assertIn('xml:lang="en-US"', us)

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
