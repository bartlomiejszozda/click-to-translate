import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from llm_client import (
    LLMResponseError,
    complete_chat,
    get_api_key,
    recent_chat_messages,
)


class LLMClientTests(unittest.TestCase):
    def test_api_key_is_stripped(self) -> None:
        with patch.dict("os.environ", {"API_KEY": "  secret  "}, clear=True):
            self.assertEqual(get_api_key(), "secret")

    def test_whitespace_api_key_is_rejected(self) -> None:
        with patch.dict("os.environ", {"API_KEY": "   "}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "No API key found"):
                get_api_key()

    def test_complete_chat_returns_text(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content="translated text"))
            ]
        )
        with patch("llm_client.get_client", return_value=client):
            result = complete_chat([{"role": "user", "content": "source"}])

        self.assertEqual(result, "translated text")

    def test_complete_chat_rejects_missing_choice(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[])
        with patch("llm_client.get_client", return_value=client):
            with self.assertRaisesRegex(LLMResponseError, "no response choice"):
                complete_chat([{"role": "user", "content": "source"}])

    def test_complete_chat_rejects_empty_content(self) -> None:
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="  "))]
        )
        with patch("llm_client.get_client", return_value=client):
            with self.assertRaisesRegex(LLMResponseError, "empty text response"):
                complete_chat([{"role": "user", "content": "source"}])

    def test_recent_chat_messages_filters_after_limiting(self) -> None:
        history = [
            {"role": "user", "content": "old"},
            {"role": "system", "content": "ignored"},
            {"role": "assistant", "content": "recent"},
            {"role": "user", "content": 123},
        ]

        self.assertEqual(
            recent_chat_messages(history, limit=3),
            [{"role": "assistant", "content": "recent"}],
        )


if __name__ == "__main__":
    unittest.main()
