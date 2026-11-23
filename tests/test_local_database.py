import tempfile
import unittest
from pathlib import Path

from helper.database import Database


class LocalDatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db = Database(str(Path(self.temp_dir.name) / "test.sqlite3"))

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_user_settings_persist(self):
        await self.db.set_format_template(112233, "Naruto S{season}E{episode} {quality}")
        await self.db.set_caption(112233, "**{filename}**")
        await self.db.set_thumbnail(112233, "telegram-file-id")
        self.assertEqual(await self.db.get_metadata(112233), "Off")
        self.assertEqual(await self.db.get_format_template(112233), "Naruto S{season}E{episode} {quality}")
        self.assertEqual(await self.db.get_caption(112233), "**{filename}**")
        self.assertEqual(await self.db.get_thumbnail(112233), "telegram-file-id")

    async def test_missing_metadata_setting_defaults_to_preserve_original(self):
        user_id = 456789
        await self.db._run(self._insert_legacy_user_without_metadata, user_id)
        self.assertEqual(await self.db.get_metadata(user_id), "Off")

    def _insert_legacy_user_without_metadata(self, user_id):
        import json
        with self.db._connection() as connection:
            connection.execute(
                "INSERT INTO users(user_id, data) VALUES(?, ?)",
                (user_id, json.dumps({"format_template": None})),
            )

    async def test_metadata_settings_persist(self):
        user_id = 445566
        await self.db.set_title(user_id, "Series title")
        await self.db.set_author(user_id, "Author tag")
        await self.db.set_artist(user_id, "Artist tag")
        await self.db.set_audio(user_id, "Audio tag")
        await self.db.set_subtitle(user_id, "Subtitle tag")
        await self.db.set_video(user_id, "Video tag")
        self.assertEqual(await self.db.get_title(user_id), "Series title")
        self.assertEqual(await self.db.get_author(user_id), "Author tag")
        self.assertEqual(await self.db.get_artist(user_id), "Artist tag")
        self.assertEqual(await self.db.get_audio(user_id), "Audio tag")
        self.assertEqual(await self.db.get_subtitle(user_id), "Subtitle tag")
        self.assertEqual(await self.db.get_video(user_id), "Video tag")

    async def test_sort_queue_session_lifecycle(self):
        user_id = 223344
        await self.db.start_sort_session(user_id)
        self.assertTrue(await self.db.is_sort_session_active(user_id))
        first = await self.db.add_sort_file(user_id, 123, 10, "file1", "Naruto 02 1080p.mkv", "document")
        second = await self.db.add_sort_file(user_id, 123, 11, "file2", "Naruto 01 480p.mkv", "document")
        duplicate = await self.db.add_sort_file(user_id, 123, 11, "file2", "Naruto 01 480p.mkv", "document")
        self.assertEqual((first, second, duplicate), (1, 2, 2))

        await self.db.stop_sort_session(user_id)
        self.assertFalse(await self.db.is_sort_session_active(user_id))
        queued = await self.db.get_sort_files(user_id)
        self.assertEqual([item["message_id"] for item in queued], [10, 11])

        await self.db.mark_sort_file_sent(user_id, 123, 10)
        retry_queue = await self.db.get_sort_files(user_id)
        self.assertEqual([item["message_id"] for item in retry_queue], [11])

        await self.db.finish_sort_session(user_id)
        self.assertEqual(await self.db.get_sort_files(user_id), [])

    async def test_new_sort_session_clears_old_queue(self):
        user_id = 334455
        await self.db.start_sort_session(user_id)
        await self.db.add_sort_file(user_id, 123, 10, "file1", "Naruto 01 480p.mkv", "document")
        await self.db.start_sort_session(user_id)
        self.assertEqual(await self.db.get_sort_files(user_id), [])


if __name__ == "__main__":
    unittest.main()
