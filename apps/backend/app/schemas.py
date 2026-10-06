from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AutomationCreate(BaseModel):
    code: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    system: str | None = Field(default=None, min_length=1, max_length=100)


class AutomationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    system: str | None
    status: str
    current_version: int | None
    created_at: datetime
    updated_at: datetime


class AutomationListResponse(BaseModel):
    items: list[AutomationRead]
    total: int
    limit: int
    offset: int
