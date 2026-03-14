"""Auth utilities — JWT verification via Supabase."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from app.core.supabase import get_supabase_client


async def get_current_user(request: Request) -> dict:
    """Extract and verify user from Authorization header using Supabase."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = auth_header.split(" ", 1)[1]
    db = get_supabase_client()

    try:
        user_response = db.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"id": str(user_response.user.id), "email": user_response.user.email}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
