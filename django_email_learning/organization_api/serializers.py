from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from django_email_learning.models import Enrollment
from django_email_learning.public.api.serializers import EmailValidatedRequest


class EnrollmentCreateRequest(EmailValidatedRequest):
    course_slug: str = Field(min_length=1)
    subscribe_to_newsletter: bool = Field(
        default=False, description="Whether the learner should be subscribed to the newsletter."
    )

    @field_validator("email")
    def normalize_email(cls, value: str) -> str:
        # Learner.save() lowercases on write, so normalizing here keeps the
        # lookup and the stored row agreeing on the same address.
        return value.lower()


class EnrollmentResponse(BaseModel):
    id: int = Field(ge=1, description="The unique identifier of the enrollment.")
    email: str = Field(description="The email address of the learner to be enrolled.")
    course_slug: str = Field(description="The slug of the course the learner is enrolled in.")
    status: str = Field(description="The status of the enrollment.")
    enrolled_at: datetime = Field(description="The timestamp when the learner was enrolled.")
    activated_at: Optional[datetime] = Field(
        default=None, description="The timestamp when the enrollment was activated."
    )

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


class EnrollmentCreatedResponse(BaseModel):
    status: Literal["enrolled"] = "enrolled"
    enrollment: Optional[EnrollmentResponse] = None


class AlreadyEnrolledResponse(BaseModel):
    status: Literal["already_enrolled"] = "already_enrolled"


class PingResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    error: str


class ErrorWithReferenceResponse(ErrorResponse):
    """Errors whose detail is withheld from the caller and logged instead.

    `error_id` correlates the response an integrator reports back to the full
    detail in the server logs - see `django_email_learning.error_responses`.
    """

    error_id: str
