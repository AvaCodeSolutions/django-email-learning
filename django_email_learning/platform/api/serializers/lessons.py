from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal


class LessonCreate(BaseModel):
    title: str
    content: str
    type: Literal["lesson"] = "lesson"


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class LessonResponse(BaseModel):
    id: int
    title: str
    content: str

    model_config = ConfigDict(from_attributes=True)
