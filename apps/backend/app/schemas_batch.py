from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas_execution import CorporateCredential

class BatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    automation_id: int = Field(ge=1)
    version: int = Field(ge=1)
    inputs: dict = Field(default_factory=dict)
    period_start: datetime | None = None
    period_end: datetime | None = None
    test_mode: bool = True
    keep_local_copy: bool = True
    send_to_network: bool = False
    overwrite_existing: bool = False

class BatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=16, max_length=128)
    items: list[BatchItem] = Field(min_length=1, max_length=20)
    profile_credentials: dict[str, CorporateCredential] = Field(default_factory=dict, repr=False, max_length=20)
