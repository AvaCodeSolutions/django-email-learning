from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from django_email_learning.models import Enrollment, EnrollmentStatus, waiting_gate_delivery
from django_email_learning.public.api.serializers import EmailValidatedRequest


class EnrollmentCreateRequest(EmailValidatedRequest):
    course_slug: str = Field(min_length=1)
    subscribe_to_newsletter: bool = Field(
        default=False, description="Whether the learner should be subscribed to the newsletter."
    )
    verified: bool = Field(
        default=True,
        description=(
            "Whether the enrollment is created already verified. A verified enrollment starts "
            "active and its first content is scheduled straight away, with no verification email. "
            "Set to false to have the learner confirm their address first: the enrollment then "
            "starts unverified and becomes active once they follow the emailed link."
        ),
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
    waiting_at_gate: Optional[str] = Field(
        default=None,
        description=(
            "The key of the gate the learner is waiting at, if their progress is held at one. "
            "The enrollment's status stays `active` while it waits."
        ),
    )

    @staticmethod
    def from_django_model(enrollment: Enrollment) -> "EnrollmentResponse":
        waiting = waiting_gate_delivery(enrollment) if enrollment.status == EnrollmentStatus.ACTIVE else None
        return EnrollmentResponse.model_validate(
            {
                "id": enrollment.id,
                "email": enrollment.learner.email,
                "course_slug": enrollment.course.slug,
                "status": enrollment.status,
                "enrolled_at": enrollment.enrolled_at,
                "activated_at": enrollment.activated_at,
                "waiting_at_gate": waiting.course_content.gate.key if waiting and waiting.course_content.gate else None,
            }
        )

    model_config = ConfigDict(from_attributes=True)


class EnrollmentCreatedResponse(BaseModel):
    status: Literal["enrolled"] = "enrolled"
    enrollment: Optional[EnrollmentResponse] = None


class AlreadyEnrolledResponse(BaseModel):
    status: Literal["already_enrolled"] = "already_enrolled"


class GateUnlockRequest(BaseModel):
    gate: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description=(
            "The key of the gate to unlock. Naming it is recommended: it also unlocks a gate the "
            "learner has not reached yet, so they pass straight through when they get there, and a "
            "late or retried call can never open a different gate than the one it was meant for. "
            "When omitted, the gate the learner is currently waiting at is unlocked."
        ),
        examples=["payment"],
    )


class GateUnlockResponse(BaseModel):
    status: Literal["unlocked", "unlocked_in_advance", "already_unlocked"] = Field(
        description=(
            "`unlocked`: the learner was waiting at the gate and has moved on. "
            "`unlocked_in_advance`: the learner has not reached the gate yet and will pass it without "
            "stopping. `already_unlocked`: nothing changed; the gate was unlocked before."
        )
    )
    gate: str = Field(description="The key of the gate that was unlocked.")
    enrollment: EnrollmentResponse


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
