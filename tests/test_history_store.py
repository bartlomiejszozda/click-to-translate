import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from history_store import (
    add_learning_chat_exchange,
    create_translation,
    get_learning_chat_messages,
    get_revisions,
    get_translation,
    list_source_texts_for_export,
    mark_source_texts_exported,
    update_learning_suggestions,
)


class HistoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        db_path = Path(self.temporary_directory.name) / "translations.sqlite3"
        self.environment = patch.dict(
            os.environ,
            {"TRANSLATOR_DB_PATH": str(db_path)},
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary_directory.cleanup()

    def create_item(self) -> int:
        return create_translation(
            source_text="source",
            translated_text="translation",
            target_language="English",
            model="test-model",
            origin="test",
        )

    def test_create_translation_also_creates_initial_revision(self) -> None:
        translation_id = self.create_item()

        item = get_translation(translation_id)
        revisions = get_revisions(translation_id)

        self.assertIsNotNone(item)
        self.assertEqual(item["current_translation"], "translation")
        self.assertEqual(len(revisions), 1)
        self.assertEqual(revisions[0]["note"], "Initial translation")

    def test_learning_content_is_persisted(self) -> None:
        translation_id = self.create_item()

        update_learning_suggestions(translation_id, "study this")
        add_learning_chat_exchange(translation_id, "why?", "because")

        item = get_translation(translation_id)
        messages = get_learning_chat_messages(translation_id)
        self.assertEqual(item["learning_suggestions"], "study this")
        self.assertEqual(
            [(message["role"], message["content"]) for message in messages],
            [("user", "why?"), ("assistant", "because")],
        )

    def test_export_marker_is_persisted(self) -> None:
        translation_id = self.create_item()
        mark_source_texts_exported([translation_id])

        items = list_source_texts_for_export()

        self.assertEqual(len(items), 1)
        self.assertIsNotNone(items[0]["source_exported_at"])


if __name__ == "__main__":
    unittest.main()
