"""Local pairing and server-owned cookie sessions."""
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from app.config import get_settings
from app.errors import ApiError
from app.local_pairing import pairing_authority
from app.security import SESSION_COOKIE_NAME, issue_session, resolve_session, revoke_session

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pairing_code: SecretStr = Field(min_length=1, max_length=128, repr=False)


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    if not pairing_authority.consume(payload.pairing_code.get_secret_value()):
        raise ApiError(401, "INVALID_PAIRING_CODE", "Código inválido, utilizado ou expirado.")
    settings = get_settings()
    ttl = max(1, min(settings.auth_session_ttl_seconds, 28800))
    token = issue_session("local", ttl)
    response.set_cookie(key=SESSION_COOKIE_NAME, value=token, max_age=ttl,
        httponly=True, secure=settings.auth_cookie_secure, samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True, "username": "local"}


@router.get("/session")
def session(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    username = resolve_session(request.cookies.get(SESSION_COOKIE_NAME))
    return {"authenticated": username is not None, "username": username}


@router.post("/logout")
def logout(request: Request, response: Response):
    revoke_session(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(key=SESSION_COOKIE_NAME, httponly=True,
        secure=get_settings().auth_cookie_secure, samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": False, "username": None}
