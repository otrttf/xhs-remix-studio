from functools import lru_cache
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ModuleNotFoundError:
    pass


class Settings:
    app_name = "Xiaohongshu Remix Studio"
    database_path = None
    images_dir = None
    ai_provider = os.getenv("AI_PROVIDER", "openai").lower()
    opencli_bin = os.getenv("OPENCLI_BIN", "opencli")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    minimax_api_key = os.getenv("MINIMAX_API_KEY", "")
    minimax_model = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
    minimax_base_url = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
    openai_timeout = float(os.getenv("OPENAI_TIMEOUT", "45"))
    mock_ai = os.getenv("MOCK_AI", "false").lower() == "true"

    def __init__(self):
        self.database_path = self._project_path(os.getenv("DATABASE_PATH", "data/app.db"))
        self.images_dir = self._project_path(os.getenv("IMAGES_DIR", "data/images"))

    @staticmethod
    def _project_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else BASE_DIR / path


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    settings.images_dir.mkdir(parents=True, exist_ok=True)
    return settings
