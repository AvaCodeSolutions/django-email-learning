from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from django_email_learning.models import Course, Enrollment
from django_email_learning.public.api.serializers import EmailValidatedRequest


class EnrollmentCreateRequest(EmailValidatedRequest):
    course_slug: str = Field(min_length=1)
    subscribe_to_newsletter: bool = False

    @field_validator("email")
    def normalize_email(cls, value: str) -> str:
        # Learner.save() lowercases on write, so normalizing here keeps the
        # lookup and the stored row agreeing on the same address.
        return value.lower()


class CourseResponse(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str] = None
    language: str
    enabled: bool
    is_public: bool

    @staticmethod
    def from_django_model(course: Course) -> "CourseResponse":
        return CourseResponse.model_validate(
            {
                "id": course.id,
                "slug": course.slug,
                "title": course.title,
                "description": course.description,
                "language": course.language,
                "enabled": course.enabled,
                "is_public": course.is_public,
            }
        )

    model_config = ConfigDict(from_attributes=True)


class EnrollmentResponse(BaseModel):
    id: int
    email: str
    course_slug: str
    status: str
    enrolled_at: datetime
    activated_at: Optional[datetime] = None

    @staticmethod
    def from_django_model(enrollment: Enrollment) -> "EnrollmentResponse":
        return EnrollmentResponse.model_validate(
            {
                "id": enrollment.id,
                "email": enrollment.learner.email,
                "course_slug": enrollment.course.slug,
                "status": enrollment.status,
                "enrolled_at": enrollment.enrolled_at,
                "activated_at": enrollment.activated_at,
            }
        )

    model_config = ConfigDict(from_attributes=True)


class EnrollmentListQuery(BaseModel):
    """Query-string parameters for listing enrollments.

    `limit` is capped rather than unbounded so a caller can't turn one request
    into a full table scan of a large organization.
    """

    course_slug: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    @field_validator("email")
    def normalize_email(cls, value: Optional[str]) -> Optional[str]:
        return value.lower() if value else value


class PaginatedEnrollmentsResponse(BaseModel):
    enrollments: List[EnrollmentResponse]
    total: int
    limit: int
    offset: int
