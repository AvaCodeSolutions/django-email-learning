import enum
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from django_email_learning.models import AssignmentSubmission
from django_email_learning.platform.api.serializers.common import (
    InstructorResponse,
    LearnerResponse,
)


class AssignmentCreate(BaseModel):
    title: str
    description: str
    is_blocking: bool
    deadline_days: int = Field(ge=0, examples=[14])
    requires_text_submission: bool
    requires_file_submission: bool
    type: Literal["assignment"] = "assignment"
    reminder_interval_days: Optional[int] = Field(default=None, examples=[3])


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_blocking: Optional[bool] = None
    deadline_days: Optional[int] = Field(ge=0, examples=[14], default=None)
    requires_text_submission: Optional[bool] = None
    requires_file_submission: Optional[bool] = None
    reminder_interval_days: Optional[int] = Field(default=None, examples=[3])

    model_config = ConfigDict(extra="forbid")


class AssignmentResponse(BaseModel):
    id: int
    title: str
    description: str
    is_blocking: bool
    deadline_days: int
    requires_text_submission: bool
    requires_file_submission: bool
    reminder_interval_days: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class ReviewResult(enum.StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUESTING_CHANGES = "requesting_changes"


class ReviewRquest(BaseModel):
    review_result: ReviewResult
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    comment: str
    provided_by: InstructorResponse
    provided_at: datetime


class AssignmentSubmissionResponse(BaseModel):
    id: int
    assignment_title: str
    submitted_at: datetime
    status: AssignmentSubmission.SubmissionStatus
    learner: LearnerResponse
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[InstructorResponse] = None
    file_submission: Optional[str] = None
    text_submission: Optional[str] = None
    file_name: Optional[str] = None
    feedbacks: list[FeedbackResponse] = []

    @staticmethod
    def from_django_model(
        submission: AssignmentSubmission,
        request: Any,
    ) -> "AssignmentSubmissionResponse":
        return AssignmentSubmissionResponse(
            id=submission.id,
            assignment_title=submission.delivery.course_content.assignment.title,  # type: ignore[union-attr]
            submitted_at=submission.submitted_at,
            learner=LearnerResponse(
                id=submission.delivery.enrollment.learner.id,  # type: ignore[union-attr]
                email=submission.delivery.enrollment.learner.email,  # type: ignore[union-attr]
                photo=submission.delivery.enrollment.learner.photo,
            ),
            status=AssignmentSubmission.SubmissionStatus(submission.status),
            reviewed_at=submission.reviewed_at,
            reviewed_by=InstructorResponse(
                display_name=submission.reviewer.display_name or submission.reviewer.user.email,  # type: ignore[union-attr]
                photo=request.build_absolute_uri(submission.reviewer.photo.url) if submission.reviewer.photo else None,
            )
            if submission.reviewer
            else None,  # type: ignore[union-attr]
            file_submission=submission.private_file_url(),
            file_name=submission.file_submission.name.split("/")[-1]
            if submission.file_submission and submission.file_submission.name
            else None,
            text_submission=submission.text_submission,
            feedbacks=[
                FeedbackResponse(
                    comment=feedback.comment,
                    provided_by=InstructorResponse(
                        display_name=feedback.provided_by.display_name  # type: ignore[union-attr]
                        or feedback.provided_by.user.email,  # type: ignore[union-attr]
                        photo=request.build_absolute_uri(feedback.provided_by.photo.url)
                        if feedback.provided_by.photo
                        else None,
                    ),
                    provided_at=feedback.provided_at,
                )
                for feedback in submission.feedbacks.all()
                if feedback.provided_by  # type: ignore[union-attr]
            ],
        )


class AssignmentSubmissionSummaryResponse(BaseModel):
    id: int
    assignment_title: str
    learner: LearnerResponse
    submitted_at: datetime
    status: AssignmentSubmission.SubmissionStatus
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    @staticmethod
    def from_django_model(
        submission: AssignmentSubmission,
    ) -> "AssignmentSubmissionSummaryResponse":
        return AssignmentSubmissionSummaryResponse(
            id=submission.id,
            assignment_title=submission.delivery.course_content.assignment.title,  # type: ignore[union-attr]
            learner=LearnerResponse(
                id=submission.delivery.enrollment.learner.id,  # type: ignore[union-attr]
                email=submission.delivery.enrollment.learner.email,  # type: ignore[union-attr]
                photo=submission.delivery.enrollment.learner.photo,
            ),
            submitted_at=submission.submitted_at,
            status=AssignmentSubmission.SubmissionStatus(submission.status),
            reviewed_at=submission.reviewed_at,
            reviewed_by=submission.reviewer.display_name if submission.reviewer else None,  # type: ignore[union-attr]
        )
