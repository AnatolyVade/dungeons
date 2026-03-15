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


def maybe_single_data(query):
    """Safe maybe_single: returns the row dict or None.

    supabase-py's maybe_single() can return None instead of an object
    with .data=None in some versions. This helper handles both cases.
    """
    try:
        result = query.maybe_single().execute()
        if result is None:
            return None
        return result.data
    except Exception:
        # If maybe_single fails, fall back to regular query
        result = query.execute()
        if result and result.data:
            return result.data[0]
        return None
