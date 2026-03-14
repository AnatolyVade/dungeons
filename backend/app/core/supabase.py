from supabase import create_client, Client
from app.core.config import get_settings


def get_supabase_client() -> Client:
    """Get Supabase client with service role key (bypasses RLS)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


def get_supabase_anon_client() -> Client:
    """Get Supabase client with anon key (respects RLS)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)
