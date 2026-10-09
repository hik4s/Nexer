from fastapi import APIRouter, Request, Response
from app.errors import ApiError
from app.worker_channel import worker_channel

router = APIRouter(prefix="/internal/credentials", tags=["Internal"])


@router.get("/{execution_id}/{system}")
def resolve(execution_id: int, system: str, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    try:
        return worker_channel.resolve(execution_id, system, request.headers.get("x-nexer-worker"))
    except RuntimeError:
        raise ApiError(401, "CREDENTIALS_UNAVAILABLE", "Credenciais indisponíveis.") from None


@router.post("/{execution_id}/release")
def release(execution_id: int, request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    try:
        worker_channel.release(execution_id, request.headers.get("x-nexer-worker"))
    except RuntimeError:
        raise ApiError(401, "CREDENTIALS_UNAVAILABLE", "Credenciais indisponíveis.") from None
    return {"released": True}
