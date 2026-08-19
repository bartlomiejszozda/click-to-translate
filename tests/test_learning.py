import unittest
from unittest.mock import patch

from learning import continue_learning_chat, generate_learning_suggestions


class LearningTests(unittest.TestCase):
    def test_generate_suggestions_requires_both_texts(self) -> None:
        with patch("learning.complete_chat") as complete:
            self.assertEqual(generate_learning_suggestions("", "translation"), "")
            self.assertEqual(generate_learning_suggestions("source", "   "), "")
        complete.assert_not_called()

    def test_generate_suggestions_uses_external_prompt(self) -> None:
        with patch("learning.complete_chat", return_value="lessons") as complete:
            result = generate_learning_suggestions(
                "  source text  ",
                "  translated text  ",
                " Polish ",
            )

        self.assertEqual(result, "lessons")
        messages = complete.call_args.args[0]
        self.assertIn("Polish", messages[0]["content"])
        self.assertIn("source text", messages[1]["content"])
        self.assertIn("translated text", messages[1]["content"])

    def test_learning_chat_adds_context_history_and_question(self) -> None:
        history = [
            {"role": "user", "content": f"question {index}"} for index in range(22)
        ]

        with patch("learning.complete_chat", return_value="answer") as complete:
            result = continue_learning_chat(
                source_text="source",
                translated_text="translation",
                learning_suggestions="",
                user_message="  explain this  ",
                chat_messages=history,
            )

        self.assertEqual(result, "answer")
        messages = complete.call_args.args[0]
        self.assertIn("source", messages[1]["content"])
        self.assertIn("translation", messages[1]["content"])
        self.assertEqual(messages[2]["content"], "question 2")
        self.assertEqual(messages[-1], {"role": "user", "content": "explain this"})
        self.assertEqual(len(messages), 23)

    def test_learning_chat_ignores_empty_question(self) -> None:
        with patch("learning.complete_chat") as complete:
            self.assertEqual(
                continue_learning_chat("source", "translation", "notes", " "),
                "",
            )
        complete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
