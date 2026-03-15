"""Auth routes — register, login, me."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_anon_client
from app.core.auth import get_current_user
from app.models.schemas import RegisterRequest, LoginRequest, AuthResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    db = get_supabase_anon_client()
    try:
        result = db.auth.sign_up({"email": body.email, "password": body.password})
        if not result.user:
            raise HTTPException(status_code=400, detail="Registration failed")

        # If email confirmation is enabled, session will be None.
        # Auto-login after registration to get a session.
        if not result.session:
            login_result = db.auth.sign_in_with_password(
                {"email": body.email, "password": body.password}
            )
            if not login_result.session:
                raise HTTPException(status_code=400, detail="Registration succeeded but login failed")
            return AuthResponse(
                access_token=login_result.session.access_token,
                user_id=str(login_result.user.id),
            )

        return AuthResponse(
            access_token=result.session.access_token,
            user_id=str(result.user.id),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    db = get_supabase_anon_client()
    try:
        result = db.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        if not result.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return AuthResponse(
            access_token=result.session.access_token,
            user_id=str(result.user.id),
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user_id": user["id"], "email": user["email"]}
