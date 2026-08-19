import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import prompt_loader
from prompt_loader import PromptTemplateError, load_prompt, render_prompt


class PromptLoaderTests(unittest.TestCase):
    def test_all_application_prompts_load(self) -> None:
        for name in (
            "translation",
            "translation_chat",
            "learning_suggestions",
            "learning_chat",
        ):
            with self.subTest(name=name):
                self.assertTrue(load_prompt(name).system)

    def test_render_prompt_substitutes_runtime_values(self) -> None:
        prompt = render_prompt(
            "learning_suggestions",
            source_text="I {write} text",
            translated_text="I write text",
            target_language="English",
        )

        self.assertIn("English", prompt.system)
        self.assertIn("I {write} text", prompt.user or "")

    def test_invalid_prompt_name_is_rejected(self) -> None:
        with self.assertRaises(PromptTemplateError):
            load_prompt("../secret")

    def test_missing_render_value_has_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prompt_path = Path(directory) / "example.txt"
            prompt_path.write_text("[SYSTEM]\nHello {name}\n", encoding="utf-8")
            with patch.object(prompt_loader, "PROMPTS_DIR", Path(directory)):
                with self.assertRaisesRegex(
                    PromptTemplateError, "Could not render prompt template"
                ):
                    render_prompt("example")


if __name__ == "__main__":
    unittest.main()
