from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Media storage
    media_dir: str = "/opt/projects/dungeons/media"
    media_url_prefix: str = "/media"

    # App
    debug: bool = True

    model_config = {
        "env_file": os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
