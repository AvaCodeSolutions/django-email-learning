from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from django_email_learning.models import GateTimeoutAction
from django_email_learning.services.sanitize import sanitize_rich_text

GATE_KEY_PATTERN = r"^[-a-zA-Z0-9_]+$"


class GateCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    key: str = Field(min_length=1, max_length=100, pattern=GATE_KEY_PATTERN, examples=["payment"])
    message: str = ""
    timeout_days: int = Field(default=0, ge=0, examples=[14])
    timeout_action: GateTimeoutAction = GateTimeoutAction.DEACTIVATE
    type: Literal["gate"] = "gate"

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, value: str) -> str:
        return sanitize_rich_text(value) if value else value


class GateUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    key: Optional[str] = Field(default=None, min_length=1, max_length=100, pattern=GATE_KEY_PATTERN)
    message: Optional[str] = None
    timeout_days: Optional[int] = Field(default=None, ge=0)
    timeout_action: Optional[GateTimeoutAction] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, value: Optional[str]) -> Optional[str]:
        return sanitize_rich_text(value) if value else value


class GateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    key: str
    message: str
    timeout_days: int
    timeout_action: str
