import os
import tempfile
import unittest
from pathlib import Path

from app.database import get_db, init_db


class DatabaseSmokeTest(unittest.TestCase):
    def test_init_db_creates_default_persona(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["DATABASE_PATH"] = str(Path(temp_dir) / "app.db")
            from app.config import get_settings

            get_settings.cache_clear()
            init_db()
            with get_db() as conn:
                persona = conn.execute("SELECT name FROM personas LIMIT 1").fetchone()
                self.assertEqual(persona["name"], "小白")


if __name__ == "__main__":
    unittest.main()
