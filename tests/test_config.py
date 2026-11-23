import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import Config


class ConfigValidationTests(unittest.TestCase):
    def _set_minimal_runtime_config(self, storage_dir):
        patches = [
            patch.object(Config, "STORAGE_DIR", str(storage_dir)),
            patch.object(Config, "BOT_TOKEN", "123:fake-token"),
            patch.object(Config, "OWNER_ID", 111),
            patch.object(Config, "ADMIN_ID_RAW", "222"),
            patch.object(Config, "ADMIN_IDS", [111, 222]),
            patch.object(Config, "API_ID", ""),
            patch.object(Config, "API_HASH", ""),
        ]
        return patches

    def test_three_runtime_variables_work_with_existing_session(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "auto_rename_bot.session"
            session.touch()
            patches = self._set_minimal_runtime_config(directory)
            for item in patches:
                item.start()
            try:
                Config.validate()
            finally:
                for item in reversed(patches):
                    item.stop()

    def test_fresh_session_requires_api_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            patches = self._set_minimal_runtime_config(directory)
            for item in patches:
                item.start()
            try:
                with self.assertRaisesRegex(RuntimeError, "API_ID, API_HASH"):
                    Config.validate()
            finally:
                for item in reversed(patches):
                    item.stop()


if __name__ == "__main__":
    unittest.main()
