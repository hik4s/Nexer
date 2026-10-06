from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class ExecutionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    requested_by: str | None = Field(default=None, min_length=1, max_length=200)
    period_start: datetime | None = None
    period_end: datetime | None = None
    automation_ids: list[int] = Field(min_length=1)
    send_to_network: bool = False
    keep_local_copy: bool = True
    overwrite_existing: bool = False
    test_mode: bool = False

    @field_validator("automation_ids")
    @classmethod
    def validate_unique_automation_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("automation_ids must be unique")
        return value

    @model_validator(mode="after")
    def validate_period(self):
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_start > self.period_end
        ):
            raise ValueError("period_start must be before period_end")
        return self


class ExecutionAutomationRead(BaseModel):
    id: int
    execution_id: int
    automation_id: int
    automation_version: int
    status: str
    stage: str
    attempts: int
    last_progress_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    error_type: str | None
    error_detail: str | None


class ExecutionRead(BaseModel):
    id: int
    name: str
    requested_by: str | None
    period_start: datetime | None
    period_end: datetime | None
    status: str
    send_to_network: bool
    keep_local_copy: bool
    overwrite_existing: bool
    test_mode: bool
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    cancel_requested: bool
    items: list[ExecutionAutomationRead]


class ExecutionListResponse(BaseModel):
    items: list[ExecutionRead]
    total: int
    limit: int
    offset: int
