from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from django_email_learning.services.sanitize import sanitize_rich_text


class LessonCreate(BaseModel):
    title: str
    content: str
    type: Literal["lesson"] = "lesson"

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, value: str) -> str:
        return sanitize_rich_text(value)


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, value: Optional[str]) -> Optional[str]:
        return sanitize_rich_text(value) if value else value


class LessonResponse(BaseModel):
    id: int
    title: str
    content: str

    model_config = ConfigDict(from_attributes=True)
