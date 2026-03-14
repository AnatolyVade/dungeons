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

    # Redis
    redis_url: str = "redis://localhost:6379"

    # App
    debug: bool = True

    model_config = {"env_file": os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
