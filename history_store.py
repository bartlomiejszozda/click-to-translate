import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB_PATH = "data/translations.sqlite3"


def get_db_path() -> str:
    return os.getenv("TRANSLATOR_DB_PATH", DEFAULT_DB_PATH)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def connect():
    db_path = get_db_path()
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source_text TEXT NOT NULL,
                target_language TEXT NOT NULL,
                current_translation TEXT NOT NULL,
                learning_suggestions TEXT NOT NULL DEFAULT '',
                model TEXT NOT NULL,
                origin TEXT NOT NULL,
                -- Tracks copy actions performed from inside the Python app.
                -- Host-side shortcut copies can happen after docker exec returns.
                copied_to_clipboard INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                translation_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                translation_text TEXT NOT NULL,
                note TEXT NOT NULL,
                FOREIGN KEY (translation_id)
                    REFERENCES translations (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                translation_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                FOREIGN KEY (translation_id)
                    REFERENCES translations (id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS learning_chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                translation_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                FOREIGN KEY (translation_id)
                    REFERENCES translations (id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_translations_updated_at
                ON translations (updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_revisions_translation_id
                ON revisions (translation_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_translation_id
                ON chat_messages (translation_id, created_at ASC);
            CREATE INDEX IF NOT EXISTS idx_learning_chat_messages_translation_id
                ON learning_chat_messages (translation_id, created_at ASC);
            """
        )
        translation_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(translations)")
        }
        if "learning_suggestions" not in translation_columns:
            conn.execute(
                """
                ALTER TABLE translations
                ADD COLUMN learning_suggestions TEXT NOT NULL DEFAULT ''
                """
            )
        conn.commit()


def _row_to_dict(row):
    return dict(row) if row is not None else None


def create_translation(
    source_text: str,
    translated_text: str,
    target_language: str,
    model: str,
    origin: str,
    copied_to_clipboard: bool = False,
    learning_suggestions: str = "",
) -> int:
    init_db()
    now = utc_now()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO translations (
                created_at,
                updated_at,
                source_text,
                target_language,
                current_translation,
                learning_suggestions,
                model,
                origin,
                copied_to_clipboard
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                source_text,
                target_language,
                translated_text,
                learning_suggestions,
                model,
                origin,
                int(copied_to_clipboard),
            ),
        )
        translation_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO revisions (
                translation_id,
                created_at,
                translation_text,
                note
            )
            VALUES (?, ?, ?, ?)
            """,
            (translation_id, now, translated_text, "Initial translation"),
        )
        conn.commit()
        return translation_id


def list_translations(limit: int = 50):
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                created_at,
                updated_at,
                source_text,
                target_language,
                current_translation,
                learning_suggestions,
                model,
                origin,
                copied_to_clipboard
            FROM translations
            ORDER BY updated_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_translation(translation_id: int):
    init_db()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                id,
                created_at,
                updated_at,
                source_text,
                target_language,
                current_translation,
                learning_suggestions,
                model,
                origin,
                copied_to_clipboard
            FROM translations
            WHERE id = ?
            """,
            (translation_id,),
        ).fetchone()
        return _row_to_dict(row)


def get_chat_messages(translation_id: int):
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, role, content
            FROM chat_messages
            WHERE translation_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (translation_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_learning_chat_messages(translation_id: int):
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, role, content
            FROM learning_chat_messages
            WHERE translation_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (translation_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_revisions(translation_id: int):
    init_db()
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, translation_text, note
            FROM revisions
            WHERE translation_id = ?
            ORDER BY created_at DESC, id DESC
            """,
            (translation_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def update_translation_from_chat(
    translation_id: int,
    user_message: str,
    assistant_message: str,
    revised_translation: str,
) -> None:
    init_db()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (
                translation_id,
                created_at,
                role,
                content
            )
            VALUES (?, ?, ?, ?)
            """,
            (translation_id, now, "user", user_message),
        )
        conn.execute(
            """
            INSERT INTO chat_messages (
                translation_id,
                created_at,
                role,
                content
            )
            VALUES (?, ?, ?, ?)
            """,
            (translation_id, now, "assistant", assistant_message),
        )
        conn.execute(
            """
            INSERT INTO revisions (
                translation_id,
                created_at,
                translation_text,
                note
            )
            VALUES (?, ?, ?, ?)
            """,
            (translation_id, now, revised_translation, user_message),
        )
        conn.execute(
            """
            UPDATE translations
            SET current_translation = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (revised_translation, now, translation_id),
        )
        conn.commit()


def add_learning_chat_exchange(
    translation_id: int,
    user_message: str,
    assistant_message: str,
) -> None:
    init_db()
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO learning_chat_messages (
                translation_id,
                created_at,
                role,
                content
            )
            VALUES (?, ?, ?, ?)
            """,
            (translation_id, now, "user", user_message),
        )
        conn.execute(
            """
            INSERT INTO learning_chat_messages (
                translation_id,
                created_at,
                role,
                content
            )
            VALUES (?, ?, ?, ?)
            """,
            (translation_id, now, "assistant", assistant_message),
        )
        conn.execute(
            """
            UPDATE translations
            SET updated_at = ?
            WHERE id = ?
            """,
            (now, translation_id),
        )
        conn.commit()


def update_clipboard_status(translation_id: int, copied_to_clipboard: bool) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            UPDATE translations
            SET copied_to_clipboard = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (int(copied_to_clipboard), utc_now(), translation_id),
        )
        conn.commit()


def update_learning_suggestions(
    translation_id: int, learning_suggestions: str
) -> None:
    init_db()
    with connect() as conn:
        conn.execute(
            """
            UPDATE translations
            SET learning_suggestions = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (learning_suggestions, utc_now(), translation_id),
        )
        conn.commit()
