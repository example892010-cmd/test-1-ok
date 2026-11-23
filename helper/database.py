"""SQLite-backed local storage. No remote database is required."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sqlite3
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from config import Config

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path: Optional[str] = None):
        storage_dir = Path(Config.STORAGE_DIR)
        storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(Path(db_path) if db_path else storage_dir / "bot.sqlite3")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, data TEXT NOT NULL)"
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS sort_sessions (
                    user_id INTEGER PRIMARY KEY,
                    active INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS sort_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    sent INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(user_id, chat_id, message_id),
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )"""
            )
            # Upgrade databases created by the first batch-sort version.
            columns = {row[1] for row in connection.execute("PRAGMA table_info(sort_queue)")}
            if "sent" not in columns:
                connection.execute("ALTER TABLE sort_queue ADD COLUMN sent INTEGER NOT NULL DEFAULT 0")

    @staticmethod
    def new_user(user_id: int) -> Dict[str, Any]:
        return {
            "join_date": date.today().isoformat(),
            "file_id": None,
            "caption": None,
            "metadata": "Off",
            "title": "Encoded by @Animes_Cruise",
            "author": "@Animes_Cruise",
            "artist": "@Animes_Cruise",
            "audio": "By @Animes_Cruise",
            "subtitle": "By @Animes_Cruise",
            "video": "Encoded By @Animes_Cruise",
            "format_template": None,
            "media_type": None,
        }

    async def _run(self, function, *args):
        return await asyncio.to_thread(function, *args)

    def _get_sync(self, user_id: int) -> Dict[str, Any]:
        with self._connection() as connection:
            row = connection.execute("SELECT data FROM users WHERE user_id=?", (int(user_id),)).fetchone()
        if row:
            return json.loads(row["data"])
        return self.new_user(int(user_id))

    def _set_sync(self, user_id: int, key: str, value: Any):
        # Serialize JSON read/modify/write so simultaneous setting commands cannot
        # overwrite one another's changes.
        with self._write_lock:
            with self._connection() as connection:
                row = connection.execute("SELECT data FROM users WHERE user_id=?", (int(user_id),)).fetchone()
                data = json.loads(row["data"]) if row else self.new_user(int(user_id))
                data[key] = value
                connection.execute(
                    "INSERT INTO users(user_id, data) VALUES(?, ?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data",
                    (int(user_id), json.dumps(data, ensure_ascii=False)),
                )

    async def add_user(self, bot, message):
        user = message.from_user
        if not user:
            return
        inserted = await self._run(self._add_user_sync, user.id)
        if inserted:
            try:
                from .utils import send_log
                await send_log(bot, user)
            except Exception as error:
                logger.debug("New-user log skipped: %s", error)

    def _add_user_sync(self, user_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO users(user_id, data) VALUES(?, ?)",
                (int(user_id), json.dumps(self.new_user(user_id), ensure_ascii=False)),
            )
            return cursor.rowcount > 0

    async def is_user_exist(self, user_id: int) -> bool:
        return await self._run(self._exists_sync, user_id)

    def _exists_sync(self, user_id):
        with self._connection() as connection:
            return connection.execute("SELECT 1 FROM users WHERE user_id=?", (int(user_id),)).fetchone() is not None

    async def total_users_count(self) -> int:
        return await self._run(self._count_sync)

    def _count_sync(self):
        with self._connection() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])

    async def get_all_users(self) -> List[Dict[str, int]]:
        return await self._run(self._all_users_sync)

    def _all_users_sync(self):
        with self._connection() as connection:
            return [{"_id": row[0]} for row in connection.execute("SELECT user_id FROM users ORDER BY user_id")]

    async def delete_user(self, user_id: int):
        await self._run(self._delete_user_sync, user_id)

    def _delete_user_sync(self, user_id):
        with self._connection() as connection:
            connection.execute("DELETE FROM sort_queue WHERE user_id=?", (int(user_id),))
            connection.execute("DELETE FROM sort_sessions WHERE user_id=?", (int(user_id),))
            connection.execute("DELETE FROM users WHERE user_id=?", (int(user_id),))

    async def _get(self, user_id: int, key: str, default=None):
        data = await self._run(self._get_sync, user_id)
        return data.get(key, default)

    async def _set(self, user_id: int, key: str, value: Any):
        await self._run(self._set_sync, user_id, key, value)

    async def set_thumbnail(self, user_id, file_id): await self._set(user_id, "file_id", file_id)
    async def get_thumbnail(self, user_id): return await self._get(user_id, "file_id")
    async def set_caption(self, user_id, caption): await self._set(user_id, "caption", caption)
    async def get_caption(self, user_id): return await self._get(user_id, "caption")
    async def set_format_template(self, user_id, template): await self._set(user_id, "format_template", template)
    async def get_format_template(self, user_id): return await self._get(user_id, "format_template")
    async def set_media_preference(self, user_id, media_type): await self._set(user_id, "media_type", media_type)
    async def get_media_preference(self, user_id): return await self._get(user_id, "media_type")
    async def get_metadata(self, user_id): return await self._get(user_id, "metadata", "Off")
    async def set_metadata(self, user_id, metadata): await self._set(user_id, "metadata", metadata)
    async def get_title(self, user_id): return await self._get(user_id, "title", "Encoded by @Animes_Cruise")
    async def set_title(self, user_id, value): await self._set(user_id, "title", value)
    async def get_author(self, user_id): return await self._get(user_id, "author", "@Animes_Cruise")
    async def set_author(self, user_id, value): await self._set(user_id, "author", value)
    async def get_artist(self, user_id): return await self._get(user_id, "artist", "@Animes_Cruise")
    async def set_artist(self, user_id, value): await self._set(user_id, "artist", value)
    async def get_audio(self, user_id): return await self._get(user_id, "audio", "By @Animes_Cruise")
    async def set_audio(self, user_id, value): await self._set(user_id, "audio", value)
    async def get_subtitle(self, user_id): return await self._get(user_id, "subtitle", "By @Animes_Cruise")
    async def set_subtitle(self, user_id, value): await self._set(user_id, "subtitle", value)
    async def get_video(self, user_id): return await self._get(user_id, "video", "Encoded By @Animes_Cruise")
    async def set_video(self, user_id, value): await self._set(user_id, "video", value)

    async def start_sort_session(self, user_id: int):
        await self._run(self._start_sort_session_sync, user_id)

    def _start_sort_session_sync(self, user_id):
        with self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO users(user_id, data) VALUES(?, ?)",
                (int(user_id), json.dumps(self.new_user(user_id), ensure_ascii=False)),
            )
            connection.execute("DELETE FROM sort_queue WHERE user_id=?", (int(user_id),))
            connection.execute(
                "INSERT INTO sort_sessions(user_id, active, started_at) VALUES(?, 1, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET active=1, started_at=excluded.started_at",
                (int(user_id), datetime.now(timezone.utc).isoformat()),
            )

    async def is_sort_session_active(self, user_id: int) -> bool:
        return await self._run(self._is_sort_session_active_sync, user_id)

    def _is_sort_session_active_sync(self, user_id):
        with self._connection() as connection:
            row = connection.execute("SELECT active FROM sort_sessions WHERE user_id=?", (int(user_id),)).fetchone()
            return bool(row and row[0])

    async def add_sort_file(self, user_id, chat_id, message_id, file_id, file_name, media_type):
        return await self._run(self._add_sort_file_sync, user_id, chat_id, message_id, file_id, file_name, media_type)

    def _add_sort_file_sync(self, user_id, chat_id, message_id, file_id, file_name, media_type):
        with self._connection() as connection:
            active = connection.execute("SELECT active FROM sort_sessions WHERE user_id=?", (int(user_id),)).fetchone()
            if not active or not active[0]:
                return 0
            connection.execute(
                "INSERT OR IGNORE INTO sort_queue(user_id, chat_id, message_id, file_id, file_name, media_type, created_at) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (int(user_id), int(chat_id), int(message_id), str(file_id), str(file_name), str(media_type), datetime.now(timezone.utc).isoformat()),
            )
            return int(connection.execute("SELECT COUNT(*) FROM sort_queue WHERE user_id=?", (int(user_id),)).fetchone()[0])

    async def get_sort_files(self, user_id):
        return await self._run(self._get_sort_files_sync, user_id)

    def _get_sort_files_sync(self, user_id):
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT chat_id, message_id, file_id, file_name, media_type FROM sort_queue "
                "WHERE user_id=? AND sent=0 ORDER BY id",
                (int(user_id),),
            ).fetchall()
            return [dict(row) for row in rows]

    async def mark_sort_file_sent(self, user_id, chat_id, message_id):
        await self._run(self._mark_sort_file_sent_sync, user_id, chat_id, message_id)

    def _mark_sort_file_sent_sync(self, user_id, chat_id, message_id):
        with self._connection() as connection:
            connection.execute(
                "UPDATE sort_queue SET sent=1 WHERE user_id=? AND chat_id=? AND message_id=?",
                (int(user_id), int(chat_id), int(message_id)),
            )

    async def stop_sort_session(self, user_id):
        """Stop accepting new files but keep the queue until sorting succeeds."""
        await self._run(self._stop_sort_session_sync, user_id)

    def _stop_sort_session_sync(self, user_id):
        with self._connection() as connection:
            connection.execute("UPDATE sort_sessions SET active=0 WHERE user_id=?", (int(user_id),))

    async def finish_sort_session(self, user_id):
        await self._run(self._finish_sort_session_sync, user_id)

    def _finish_sort_session_sync(self, user_id):
        with self._connection() as connection:
            connection.execute("UPDATE sort_sessions SET active=0 WHERE user_id=?", (int(user_id),))
            connection.execute("DELETE FROM sort_queue WHERE user_id=?", (int(user_id),))


codeflixbots = Database()
