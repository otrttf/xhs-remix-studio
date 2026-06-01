from contextlib import contextmanager
from datetime import datetime
import sqlite3

from .config import get_settings


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


@contextmanager
def get_db():
    settings = get_settings()
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_key TEXT NOT NULL UNIQUE,
                keyword TEXT NOT NULL,
                title TEXT DEFAULT '',
                author TEXT DEFAULT '',
                content TEXT DEFAULT '',
                likes INTEGER DEFAULT 0,
                collects INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ok',
                error_message TEXT DEFAULT '',
                collected_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS note_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                local_path TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                file_size INTEGER DEFAULT 0,
                FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
                UNIQUE(note_id, local_path)
            );

            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS persona_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                persona_id INTEGER NOT NULL,
                rule_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(persona_id) REFERENCES personas(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                persona_id INTEGER NOT NULL,
                generated_title TEXT NOT NULL,
                generated_body TEXT NOT NULL,
                suggested_tags TEXT DEFAULT '',
                image_advice TEXT DEFAULT '',
                final_title TEXT DEFAULT '',
                final_body TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'generated',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY(persona_id) REFERENCES personas(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS edit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id INTEGER NOT NULL,
                persona_id INTEGER NOT NULL,
                before_title TEXT NOT NULL,
                before_body TEXT NOT NULL,
                after_title TEXT NOT NULL,
                after_body TEXT NOT NULL,
                diff_summary TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(draft_id) REFERENCES drafts(id) ON DELETE CASCADE,
                FOREIGN KEY(persona_id) REFERENCES personas(id) ON DELETE CASCADE
            );
            """
        )
        exists = conn.execute("SELECT id FROM personas LIMIT 1").fetchone()
        if not exists:
            now = now_iso()
            cursor = conn.execute(
                "INSERT INTO personas (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
                ("小白", "00后女大学生，语言生动活泼，喜欢用真实体验、轻松吐槽和口语化表达分享好吃好玩的东西。", now, now),
            )
            conn.execute(
                "INSERT INTO persona_rules (persona_id, rule_text, created_at) VALUES (?, ?, ?)",
                (cursor.lastrowid, "开头先给一个情绪钩子，让人马上知道这家店值不值得冲。", now),
            )


def row_to_dict(row):
    return dict(row) if row else None
