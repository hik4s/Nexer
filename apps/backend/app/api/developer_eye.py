"""Authenticated, local-only developer tools; no raw browser data."""
from fastapi import APIRouter, Response
from pydantic import BaseModel, ConfigDict, Field
from app.errors import ApiError
from app.services.developer_eye import probe

router = APIRouter(prefix="/developer-eye", tags=["Developer Eye"])

class ProbeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2048)
    selector: str = Field(min_length=1, max_length=2048)

@router.post("/probe")
def probe_selector(payload: ProbeRequest, response: Response):
    try:
        result = probe(payload.url, payload.selector)
    except ValueError:
        raise ApiError(422, "DEVELOPER_PROBE_INVALID", "Revise o endereço e o seletor.") from None
    response.headers["Cache-Control"] = "no-store"
    return result
