from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from django_email_learning.models import TransitionCondition


class ContentTrackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    parent_track_id: Optional[int] = None
    merge_into_id: Optional[int] = None


class CreateContentTrackRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_track_id: Optional[int] = None
    merge_into_id: Optional[int] = None


class UpdateContentTrackRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    parent_track_id: Optional[int] = None
    merge_into_id: Optional[int] = None


class ContentTransitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    order: int
    condition: TransitionCondition
    threshold: Optional[int] = None
    target_id: int


class CreateContentTransitionRequest(BaseModel):
    order: int = Field(ge=0)
    condition: TransitionCondition
    threshold: Optional[int] = Field(default=None, ge=0, le=100)
    target_id: int
