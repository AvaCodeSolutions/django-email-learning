"""Shared serializer types imported by multiple domain modules."""

from pydantic import BaseModel, ConfigDict, field_serializer
from typing import Optional, Any
from django_email_learning.models import EnrollmentStatus


class InstructorResponse(BaseModel):
    display_name: str
    photo: Optional[str] = None


class EnrollmentsCount(BaseModel):
    total: int
    completed: int


class LearnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    photo: Optional[Any] = None
    enrollments_count: EnrollmentsCount | None = None
    enrollment_status: Optional[str] = None
    enrollment_progress: Optional[int] = None

    @field_serializer("photo")
    def serialize_photo(self, photo: Optional[Any]) -> Optional[str]:
        if photo:
            return photo.url  # type: ignore[attr-defined]
        return None


class CourseSummaryResponse(BaseModel):
    id: int
    title: str
    slug: str
    is_public: bool

    model_config = ConfigDict(from_attributes=True)


class EnrollmentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_title: str
    status: EnrollmentStatus
    progress: int
    certificate_url: str | None = None
