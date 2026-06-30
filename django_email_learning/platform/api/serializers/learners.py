import enum
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from django_email_learning.models import (
    ContentDelivery,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
    CourseContentType,
    AssignmentSubmission,
)
from django_email_learning.platform.api.serializers.common import (
    LearnerResponse,
    CourseSummaryResponse,
    EnrollmentSummaryResponse,
)
from django_email_learning.platform.api.serializers.assignments import ReviewResult


class CreateEnrollmentRequest(BaseModel):
    learner_email: str = Field(min_length=1, examples=["user@example.com"])


class EventType(enum.StrEnum):
    REGISTERED = "registered"
    VERIFIED = "verified"
    DEACTIVATED = "deactivated"
    QUIZ_SUBMITED = "quiz_submitted"
    ASSIGNMENT_SUBMITTED = "assignment_submitted"
    ASSIGNMENT_REVIEWED = "assignment_reviewed"
    CONTENT_SENT = "content_sent"
    EMAIL_OPENED = "email_opened"
    REMINDER_SENT = "reminder_sent"
    COURSE_COMPLETED = "course_completed"


class DeactivatedEvent(BaseModel):
    type: Literal[EventType.DEACTIVATED] = Field(
        default=EventType.DEACTIVATED, exclude=True
    )
    reason: str


class QuizSubmitedEvent(BaseModel):
    type: Literal[EventType.QUIZ_SUBMITED] = Field(
        default=EventType.QUIZ_SUBMITED, exclude=True
    )
    quiz_id: int
    quiz_title: str
    score: int
    is_passed: bool
    attempt_number: int
    is_practice: bool


class AssignmentSubmitedEvent(BaseModel):
    type: Literal[EventType.ASSIGNMENT_SUBMITTED] = Field(
        default=EventType.ASSIGNMENT_SUBMITTED, exclude=True
    )
    assignment_id: int
    assignment_title: str


class AssignmentReviewdEvent(BaseModel):
    type: Literal[EventType.ASSIGNMENT_REVIEWED] = Field(
        default=EventType.ASSIGNMENT_REVIEWED, exclude=True
    )
    assignment_id: int
    assignment_title: str
    review_result: ReviewResult
    reviewed_by: str


class ReminderSentEvent(BaseModel):
    type: Literal[EventType.REMINDER_SENT] = Field(
        default=EventType.REMINDER_SENT, exclude=True
    )
    content_id: int
    content_title: str


class ContentSentEvent(BaseModel):
    type: Literal[EventType.CONTENT_SENT] = Field(
        default=EventType.CONTENT_SENT, exclude=True
    )
    course_content_id: int
    course_content_title: str
    course_content_type: str


class EmailOpenedEvent(BaseModel):
    type: Literal[EventType.EMAIL_OPENED] = Field(
        default=EventType.EMAIL_OPENED, exclude=True
    )
    course_content_id: int
    course_content_title: str
    course_content_type: str


class Event(BaseModel):
    type: EventType
    timestamp: datetime
    event_data: (
        DeactivatedEvent
        | QuizSubmitedEvent
        | ContentSentEvent
        | EmailOpenedEvent
        | AssignmentSubmitedEvent
        | AssignmentReviewdEvent
        | ReminderSentEvent
        | None
    ) = Field(
        discriminator="type"
    )  # REGISTERED, VERIFIED, COURSE_COMPLETED have no additional data


class EnrollmentResponse(BaseModel):
    id: int
    learner: LearnerResponse
    course: CourseSummaryResponse
    status: EnrollmentStatus
    events: list[Event]

    @staticmethod
    def from_django_model(enrollment: Enrollment) -> "EnrollmentResponse":
        events = [
            Event(
                type=EventType.REGISTERED,
                timestamp=enrollment.enrolled_at,
                event_data=None,
            )
        ]
        if enrollment.activated_at:
            events.append(
                Event(
                    type=EventType.VERIFIED,
                    timestamp=enrollment.activated_at,
                    event_data=None,
                )
            )
        for delivery in enrollment.content_deliveries.all().order_by("id"):  # type: ignore[attr-defined]
            schedule_no = 0
            for schedule in delivery.delivery_schedules.filter(
                status=DeliveryStatus.DELIVERED
            ):
                schedule_no += 1
                events.append(
                    Event(
                        type=EventType.CONTENT_SENT,
                        timestamp=schedule.delivered_at,  # type: ignore[arg-type]
                        event_data=ContentSentEvent(
                            course_content_id=delivery.course_content.id,
                            course_content_title=delivery.course_content.title,  # type: ignore[union-attr]
                            course_content_type=delivery.course_content.type,
                        ),
                    )
                )
                if delivery.course_content.type == CourseContentType.ASSIGNMENT:
                    if (
                        delivery.reminder_state == ContentDelivery.ReminderStatus.SENT
                        and delivery.remind_at
                    ):
                        events.append(
                            Event(
                                type=EventType.REMINDER_SENT,
                                timestamp=delivery.remind_at,  # type: ignore[arg-type]
                                event_data=ReminderSentEvent(
                                    content_id=delivery.course_content.id,  # type: ignore[union-attr]
                                    content_title=delivery.course_content.title,  # type: ignore[union-attr]
                                ),
                            )
                        )
                    submission = delivery.assignment_submission  # type: ignore[attr-defined]
                    if submission:
                        events.append(
                            Event(
                                type=EventType.ASSIGNMENT_SUBMITTED,
                                timestamp=submission.submitted_at,  # type: ignore[arg-type]
                                event_data=AssignmentSubmitedEvent(
                                    assignment_id=delivery.course_content.assignment.id,  # type: ignore[union-attr]
                                    assignment_title=delivery.course_content.assignment.title,  # type: ignore[union-attr]
                                ),
                            )
                        )
                        if (
                            submission.reviewed_at
                            and submission.status
                            != AssignmentSubmission.SubmissionStatus.PENDING_REVIEW
                        ):
                            events.append(
                                Event(
                                    type=EventType.ASSIGNMENT_REVIEWED,
                                    timestamp=submission.reviewed_at,  # type: ignore[arg-type]
                                    event_data=AssignmentReviewdEvent(
                                        assignment_id=delivery.course_content.assignment.id,  # type: ignore[union-attr]
                                        assignment_title=delivery.course_content.assignment.title,  # type: ignore[union-attr]
                                        review_result=ReviewResult(submission.status),  # type: ignore[union-attr]
                                        reviewed_by=submission.reviewer.display_name,  # type: ignore[union-attr, arg-type]
                                    ),
                                )
                            )
                    # TODO:events for reminders and submissions for assignments

                if delivery.opened_at and schedule_no == 1:
                    events.append(
                        Event(
                            type=EventType.EMAIL_OPENED,
                            timestamp=delivery.opened_at,
                            event_data=EmailOpenedEvent(
                                course_content_id=delivery.course_content.id,  # type: ignore[union-attr]
                                course_content_title=delivery.course_content.title,  # type: ignore[union-attr]
                                course_content_type=delivery.course_content.type,
                            ),
                        )
                    )

                if delivery.course_content.type == CourseContentType.QUIZ:
                    if (
                        delivery.reminder_state == ContentDelivery.ReminderStatus.SENT
                        and delivery.remind_at
                    ):
                        events.append(
                            Event(
                                type=EventType.REMINDER_SENT,
                                timestamp=delivery.remind_at,  # type: ignore[arg-type]
                                event_data=ReminderSentEvent(
                                    content_id=delivery.course_content.id,  # type: ignore[union-attr]
                                    content_title=delivery.course_content.title,  # type: ignore[union-attr]
                                ),
                            )
                        )
                    attempt_number = 0
                    quiz_attempts = delivery.quiz_submissions.all().order_by(
                        "submitted_at"
                    )
                    attempt = None
                    if (
                        delivery.course_content.quiz.is_blocking  # type: ignore[union-attr]
                        and delivery.course_content.limited_attempts
                    ):
                        if schedule_no == 1:
                            attempts = [quiz_attempts.first()]
                            attempt_number = 1
                        elif schedule_no > 1:
                            attempt_number = schedule_no
                            attempts = list(quiz_attempts[1:])
                    else:
                        attempt_number = 1
                        attempts = list(quiz_attempts)
                    if attempts:
                        for attempt in [i for i in attempts if i is not None]:  # type: ignore[union-attr]
                            events.append(
                                Event(
                                    type=EventType.QUIZ_SUBMITED,
                                    timestamp=attempt.submitted_at,
                                    event_data=QuizSubmitedEvent(
                                        quiz_id=delivery.course_content.quiz.id,  # type: ignore[union-attr]
                                        quiz_title=delivery.course_content.quiz.title,  # type: ignore[union-attr]
                                        score=attempt.score,
                                        is_passed=attempt.is_passed,
                                        attempt_number=attempt_number,
                                        is_practice=delivery.course_content.quiz.is_blocking  # type: ignore[union-attr]
                                        is False,  # type: ignore[union-attr]
                                    ),
                                )
                            )
                            attempt_number += 1
        if (
            enrollment.status == EnrollmentStatus.COMPLETED
            and enrollment.final_state_at
        ):
            events.append(
                Event(
                    type=EventType.COURSE_COMPLETED,
                    timestamp=enrollment.final_state_at,
                    event_data=None,
                )
            )
        elif (
            enrollment.status == EnrollmentStatus.DEACTIVATED
            and enrollment.final_state_at
        ):
            events.append(
                Event(
                    type=EventType.DEACTIVATED,
                    timestamp=enrollment.final_state_at,
                    event_data=DeactivatedEvent(reason=enrollment.deactivation_reason),  # type: ignore[arg-type]
                )
            )

        events.sort(key=lambda e: e.timestamp)

        return EnrollmentResponse.model_validate(
            {
                "id": enrollment.id,
                "learner": enrollment.learner,
                "course": enrollment.course,
                "status": enrollment.status,
                "events": events,
            }
        )


class LearnerDetailResponse(BaseModel):
    id: int
    email: str
    enrollments: list[EnrollmentSummaryResponse]

    model_config = ConfigDict(from_attributes=True)
