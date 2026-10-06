from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AutomationVersionCreate(BaseModel):
    recipe: dict[str, Any] = Field(min_length=1)
    created_by: str | None = Field(default=None, max_length=200)


class AutomationVersionRead(BaseModel):
    id: int
    automation_id: int
    version: int
    recipe: dict[str, Any]
    created_at: datetime
    created_by: str | None
    test_status: str | None
    published: bool
    published_at: datetime | None


class AutomationVersionListResponse(BaseModel):
    items: list[AutomationVersionRead]
    total: int
    limit: int
    offset: int


class AutomationVersionTestResponse(BaseModel):
    version: int
    test_status: str
    automation_status: str


class AutomationVersionPublishResponse(BaseModel):
    version: int
    published: bool
    automation_status: str
