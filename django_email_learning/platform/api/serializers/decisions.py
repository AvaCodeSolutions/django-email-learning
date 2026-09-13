from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DecisionOptionInput(BaseModel):
    id: Optional[int] = None
    text: str = Field(min_length=1, max_length=500)


class DecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    prompt: str = Field(min_length=1)
    deadline_days: int = Field(default=0, ge=0, examples=[7])
    reminder_interval_days: Optional[int] = Field(default=None, ge=0, examples=[3])
    options: list[DecisionOptionInput] = Field(min_length=2)
    type: Literal["decision"] = "decision"


class DecisionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    prompt: Optional[str] = Field(default=None, min_length=1)
    deadline_days: Optional[int] = Field(default=None, ge=0)
    reminder_interval_days: Optional[int] = Field(default=None, ge=0)
    # The full list in order: options without an id are added, and existing ones left out are removed.
    options: Optional[list[DecisionOptionInput]] = Field(default=None, min_length=2)

    model_config = ConfigDict(extra="forbid")


class DecisionOptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    order: int


class DecisionPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    prompt: str
    deadline_days: int
    reminder_interval_days: Optional[int] = None
    options: list[DecisionOptionResponse]

    @field_validator("options", mode="before")
    @classmethod
    def options_from_manager(cls, value: Any) -> Any:
        return list(value.all()) if hasattr(value, "all") else value
