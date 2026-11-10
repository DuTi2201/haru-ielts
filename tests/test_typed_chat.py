"""Typing instead of speaking: Haru answers in text, with no Gemini Live token."""
import unittest
from unittest import mock

from app.schemas import ConversationReplyRequest, ConversationStartOut, ConversationStartRequest
from app.services import gemini_client


class TypedChatTests(unittest.TestCase):
    def test_start_request_defaults_to_speaking(self):
        self.assertFalse(ConversationStartRequest().typing)
        self.assertTrue(ConversationStartRequest(typing=True).typing)

    def test_a_typed_start_has_no_token(self):
        fields = ConversationStartOut.model_fields
        self.assertEqual(fields["token"].default, "")
        self.assertEqual(fields["ws_url"].default, "")

    def test_reply_request_may_be_empty_so_haru_opens(self):
        self.assertEqual(ConversationReplyRequest().turns, [])

    def _chat(self, turns):
        fake = mock.Mock()
        fake.models.generate_content.return_value = mock.Mock(text="  안녕하세요!  ")
        with mock.patch.object(gemini_client, "_get_client", return_value=fake), mock.patch.object(
            gemini_client.settings, "GEMINI_API_KEY", "test-key"
        ):
            out = gemini_client.generate_chat(model="m", system="sys", turns=turns)
        return out, fake.models.generate_content.call_args.kwargs

    def test_roles_map_to_user_and_model(self):
        out, kw = self._chat([{"role": "haru", "text": "안녕"}, {"role": "learner", "text": "네"}])
        self.assertEqual(out, "안녕하세요!")
        self.assertEqual([c.role for c in kw["contents"]], ["model", "user"])

    def test_an_empty_chat_asks_haru_to_open(self):
        _, kw = self._chat([])
        self.assertEqual(len(kw["contents"]), 1)
        self.assertEqual(kw["contents"][0].role, "user")
