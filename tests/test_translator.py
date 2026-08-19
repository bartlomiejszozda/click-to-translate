import unittest
from unittest.mock import patch

from translator import refine_translation, translate_text


class TranslatorTests(unittest.TestCase):
    def test_translate_empty_text_does_not_call_model(self) -> None:
        with patch("translator.complete_chat") as complete:
            self.assertEqual(translate_text("   "), "")
        complete.assert_not_called()

    def test_translate_builds_messages_from_external_prompt(self) -> None:
        with patch("translator.complete_chat", return_value="Hello") as complete:
            result = translate_text("  hallo  ", " English ")

        self.assertEqual(result, "Hello")
        messages = complete.call_args.args[0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("English", messages[0]["content"])
        self.assertEqual(messages[1], {"role": "user", "content": "hallo"})

    def test_refine_translation_limits_and_filters_history(self) -> None:
        history = [
            {"role": "user" if index % 2 == 0 else "assistant", "content": str(index)}
            for index in range(12)
        ]
        history[-2] = {"role": "system", "content": "ignore me"}

        with patch("translator.complete_chat", return_value="reply") as complete:
            result = refine_translation(
                source_text="source",
                current_translation="current",
                user_feedback="  improve it  ",
                chat_messages=history,
            )

        self.assertEqual(result, "reply")
        messages = complete.call_args.args[0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("source", messages[1]["content"])
        self.assertIn("current", messages[1]["content"])
        self.assertNotIn("ignore me", [message["content"] for message in messages])
        self.assertEqual(messages[-1], {"role": "user", "content": "improve it"})
        self.assertEqual(len(messages), 12)

    def test_refine_empty_feedback_does_not_call_model(self) -> None:
        with patch("translator.complete_chat") as complete:
            self.assertEqual(
                refine_translation("source", "translation", "   "),
                "",
            )
        complete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
