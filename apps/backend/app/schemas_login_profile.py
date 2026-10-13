from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def configured_url(value: str) -> str:
    from site_urls import validate_site_url
    try:
        return validate_site_url(value)
    except ValueError:
        raise ValueError("LOGIN_URL_INVALID") from None


def origin(value):
    parsed = urlsplit(configured_url(value))
    return f"{parsed.scheme}://{parsed.netloc}"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginTarget(StrictModel):
    selector: str = Field(min_length=1, max_length=1000)
    frames: list[str] = Field(default_factory=list, max_length=8)
    @field_validator("selector")
    @classmethod
    def nonempty(cls, value):
        if not value.strip(): raise ValueError("TARGET_INVALID")
        return value
    @field_validator("frames")
    @classmethod
    def valid_frames(cls, values):
        if any(not value.strip() or len(value) > 1000 for value in values): raise ValueError("TARGET_INVALID")
        return values


class SuccessRule(StrictModel):
    kind: Literal["marker", "url"]
    target: LoginTarget | None = None
    url: str | None = Field(default=None, max_length=2048)
    @model_validator(mode="after")
    def valid_rule(self):
        if self.kind == "marker" and (self.target is None or self.url is not None): raise ValueError("SUCCESS_RULE_INVALID")
        if self.kind == "url":
            if self.target is not None or not self.url: raise ValueError("SUCCESS_RULE_INVALID")
            self.url = configured_url(self.url)
        return self


class LoginConfiguration(StrictModel):
    login_url: str = Field(min_length=1, max_length=2048)
    allowed_origins: list[str] = Field(default_factory=list, max_length=10)
    username_target: LoginTarget | None = None
    password_target: LoginTarget | None = None
    submit_target: LoginTarget | None = None
    success_rule: SuccessRule | None = None
    @field_validator("login_url")
    @classmethod
    def valid_url(cls, value): return configured_url(value)
    @model_validator(mode="after")
    def valid_origins(self):
        normal = []
        for value in self.allowed_origins:
            parsed = urlsplit(configured_url(value))
            if parsed.path not in {"", "/"} or parsed.fragment: raise ValueError("ORIGIN_INVALID")
            normal.append(origin(value))
        self.allowed_origins = list(dict.fromkeys(normal or [origin(self.login_url)]))
        if origin(self.login_url) not in self.allowed_origins: raise ValueError("ORIGIN_INVALID")
        if self.success_rule and self.success_rule.url and origin(self.success_rule.url) not in self.allowed_origins: raise ValueError("ORIGIN_INVALID")
        return self


class LoginProfileCreate(StrictModel):
    group_id: int | None = Field(default=None, ge=1)
    template_profile_id: int | None = Field(default=None, ge=1)
    name: str = Field(min_length=1, max_length=100)
    login_url: str = Field(min_length=1, max_length=2048)
    @field_validator("login_url")
    @classmethod
    def valid_url(cls, value): return configured_url(value)
    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        if not value.strip(): raise ValueError("NAME_REQUIRED")
        return value.strip()


class ProfilePublish(StrictModel):
    version: int = Field(ge=1)
