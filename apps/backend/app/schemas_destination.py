from datetime import datetime

from pydantic import BaseModel, Field


class DestinationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    path_reference: str = Field(min_length=1, max_length=1024)
    enabled: bool = True


class DestinationUpdate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    path_reference: str = Field(min_length=1, max_length=1024)
    enabled: bool = True


class DestinationRead(BaseModel):
    id: int
    code: str
    name: str
    path_reference: str
    enabled: bool
    last_test_status: str | None
    last_test_at: datetime | None


class DestinationListResponse(BaseModel):
    items: list[DestinationRead]
    total: int
    limit: int
    offset: int
