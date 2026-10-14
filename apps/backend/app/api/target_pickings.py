from typing import Literal
from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from app.errors import ApiError
from app.security import SESSION_COOKIE_NAME
from app.services.target_pickings import target_pickings

router = APIRouter(prefix='/target-pickings', tags=['Target repair'])


class TargetStart(BaseModel):
    model_config = ConfigDict(extra='forbid')
    url: str = Field(min_length=1, max_length=2048)
    kind: Literal['element', 'text', 'select', 'checkbox', 'range', 'color']


@router.post('', status_code=201)
def start(payload: TargetStart, request: Request, response: Response):
    try:
        result = target_pickings.start_target(request.cookies.get(SESSION_COOKIE_NAME), payload.url, payload.kind)
    except (RuntimeError, ValueError):
        raise ApiError(409, 'TARGET_PICKER_UNAVAILABLE', 'Não foi possível abrir a seleção. Revise o endereço e as seleções abertas.') from None
    response.headers['Cache-Control'] = 'no-store'
    return result


@router.get('/{session_id}')
def get(session_id: str, request: Request, response: Response):
    try:
        result = target_pickings.get(session_id, request.cookies.get(SESSION_COOKIE_NAME))
    except RuntimeError:
        raise ApiError(404, 'TARGET_PICKER_NOT_FOUND', 'Seleção não encontrada nesta sessão.') from None
    response.headers['Cache-Control'] = 'no-store'
    return result


@router.post('/{session_id}/cancel')
def cancel(session_id: str, request: Request, response: Response):
    try:
        result = target_pickings.cancel(session_id, request.cookies.get(SESSION_COOKIE_NAME))
    except RuntimeError:
        raise ApiError(404, 'TARGET_PICKER_NOT_FOUND', 'Seleção não encontrada nesta sessão.') from None
    response.headers['Cache-Control'] = 'no-store'
    return result
