import os
import tempfile
import unittest
from pathlib import Path

from app.config import get_settings
from app.database import get_db, init_db
from app.image_order import display_ordered_images


class DatabaseSmokeTest(unittest.TestCase):
    def test_init_db_creates_default_persona(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["DATABASE_PATH"] = str(Path(temp_dir) / "app.db")
            get_settings.cache_clear()
            init_db()
            with get_db() as conn:
                persona = conn.execute("SELECT name FROM personas LIMIT 1").fetchone()
                self.assertEqual(persona["name"], "小白")

    def test_image_display_order_keeps_first_image_first(self):
        images = [
            {"local_path": "data/images/note/image_2.jpg", "sort_order": 2},
            {"local_path": "data/images/note/image_0.jpg", "sort_order": 0},
            {"local_path": "data/images/note/image_1.jpg", "sort_order": 1},
        ]

        ordered = display_ordered_images(images)

        self.assertEqual([image["local_path"] for image in ordered], [
            "data/images/note/image_0.jpg",
            "data/images/note/image_1.jpg",
            "data/images/note/image_2.jpg",
        ])

    def test_settings_reads_environment_after_cache_clear(self):
        previous_provider = os.environ.get("AI_PROVIDER")
        previous_base_url = os.environ.get("MINIMAX_BASE_URL")
        try:
            os.environ["AI_PROVIDER"] = "minimax"
            os.environ.pop("MINIMAX_BASE_URL", None)
            get_settings.cache_clear()

            settings = get_settings()

            self.assertEqual(settings.ai_provider, "minimax")
            self.assertEqual(settings.minimax_base_url, "https://api.minimaxi.com/v1")
        finally:
            if previous_provider is None:
                os.environ.pop("AI_PROVIDER", None)
            else:
                os.environ["AI_PROVIDER"] = previous_provider
            if previous_base_url is None:
                os.environ.pop("MINIMAX_BASE_URL", None)
            else:
                os.environ["MINIMAX_BASE_URL"] = previous_base_url
            get_settings.cache_clear()


if __name__ == "__main__":
    unittest.main()
