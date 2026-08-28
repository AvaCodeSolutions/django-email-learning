"""Shared serializer types imported by multiple domain modules."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_serializer

from django_email_learning.models import EnrollmentStatus
from django_email_learning.services.utils import resolve_private_or_public_file_url


class InstructorResponse(BaseModel):
    # OrganizationUser id - the client sends these back in UpdateCourseRequest.instructors.
    id: Optional[int] = None
    display_name: str
    photo: Optional[str] = None


class EnrollmentsCount(BaseModel):
    total: int
    completed: int


class LearnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    organization_id: int
    photo: Optional[Any] = None
    enrollments_count: EnrollmentsCount | None = None
    enrollment_status: Optional[str] = None
    enrollment_progress: Optional[int] = None

    @field_serializer("photo")
    def serialize_photo(self, photo: Optional[Any]) -> Optional[str]:
        if not photo:
            return None
        return resolve_private_or_public_file_url(organization_id=self.organization_id, file_path=photo.name)  # type: ignore[attr-defined]


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
