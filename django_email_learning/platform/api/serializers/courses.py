import enum
from typing import Callable, Optional

from django.utils.translation import get_language_info
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from django_email_learning.models import (
    Answer,
    Course,
    CourseContent,
    CourseContentType,
    CourseInstructor,
    ImapConnection,
    Lesson,
    Newsletter,
    Organization,
    OrganizationUser,
    Question,
    Quiz,
)
from django_email_learning.platform.api.serializers.assignments import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
)
from django_email_learning.platform.api.serializers.common import (
    InstructorResponse,
)
from django_email_learning.platform.api.serializers.lessons import (
    LessonCreate,
    LessonResponse,
    LessonUpdate,
)
from django_email_learning.platform.api.serializers.quizzes import (
    QuizCreate,
    QuizResponse,
    UpdateQuiz,
)
from django_email_learning.services.sanitize import strip_html


class Identifier(BaseModel):
    id: int


class PeriodType(enum.StrEnum):
    HOURS = "hours"
    DAYS = "days"


class WaitingPeriod(BaseModel):
    period: int = Field(gt=0, examples=[7])
    type: PeriodType

    def to_seconds(self) -> int:
        if self.type == PeriodType.HOURS:
            return self.period * 3600
        elif self.type == PeriodType.DAYS:
            return self.period * 86400
        else:
            raise ValueError(f"Unsupported period type: {self.type}")

    @classmethod
    def from_seconds(cls, seconds: int) -> "WaitingPeriod":
        if seconds % 86400 == 0:
            return cls(period=seconds // 86400, type=PeriodType.DAYS)
        elif seconds % 3600 == 0:
            return cls(period=seconds // 3600, type=PeriodType.HOURS)
        else:
            raise ValueError(f"Cannot convert {seconds} seconds to a valid WaitingPeriod.")


class CreateCourseRequest(BaseModel):
    title: str = Field(min_length=1, examples=["Introduction to Python"])
    slug: str = Field(
        min_length=1,
        examples=["intro-to-python"],
        description="A short label for the course, used in URLs or email interactive actions. "
        "You can not edit it later.",
    )
    description: Optional[str] = Field(None, examples=["A beginner's course on Python programming."])
    imap_connection_id: Optional[int] = Field(None, examples=[1])
    newsletter_id: Optional[int] = Field(None, examples=[1])
    image: Optional[str] = Field(None, examples=["/path/to/course_image.png"])
    language: str = Field(min_length=2, max_length=10, examples=["en"])
    target_audience: Optional[str] = Field(None, examples=["Beginners with no prior programming experience."])
    external_references: Optional[list[dict[str, str]]] = Field(
        None,
        examples=[
            [
                {
                    "name": "GitHub Repository",
                    "url": "https://github.com/AvaCodeSolutions/django-email-learning",
                },
                {
                    "name": "Documentation",
                    "url": "https://django-email-learning.readthedocs.io/",
                },
            ]
        ],
    )
    is_public: bool = Field(default=True, examples=[True])
    send_certificate: bool = Field(default=True, examples=[True])
    instructors: Optional[list[int]] = Field(
        None,
        examples=[[1, 2, 3]],
        description="List of organization user IDs to be assigned as instructors for this course.",
    )

    @field_validator("description", "target_audience")
    @classmethod
    def strip_html_markup(cls, value: Optional[str]) -> Optional[str]:
        return strip_html(value) if value else value

    def to_django_model(self, organization_id: int) -> Course:
        organization = Organization.objects.get(id=organization_id)
        if not organization:
            raise ValueError(f"Organization with id {organization_id} does not exist.")
        imap_connection = None
        if self.imap_connection_id:
            try:
                imap_connection = ImapConnection.objects.get(id=self.imap_connection_id, organization=organization)
            except ImapConnection.DoesNotExist:
                raise ValueError(f"ImapConnection with id {self.imap_connection_id} does not exist.")
            imap_connection = ImapConnection.objects.get(id=self.imap_connection_id, organization=organization)
        course = Course(
            title=self.title,
            slug=self.slug,
            description=self.description,
            organization=organization,
            language=self.language,
            is_public=self.is_public,
            send_certificate=self.send_certificate,
        )
        if imap_connection:
            course.imap_connection = imap_connection
        if self.newsletter_id:
            try:
                course.newsletter = Newsletter.objects.get(id=self.newsletter_id, organization=organization)
            except Newsletter.DoesNotExist:
                raise ValueError(f"Newsletter with id {self.newsletter_id} does not exist.")
        if self.instructors:
            course.save()  # Save course before adding instructors
            for instructor_id in self.instructors:
                try:
                    org_user = OrganizationUser.objects.get(id=instructor_id, organization=organization)
                except OrganizationUser.DoesNotExist:
                    raise ValueError(
                        f"OrganizationUser with id {instructor_id} does not exist in organization {organization.name}."
                    )
                if not org_user.can_act_as_instructor():
                    raise ValueError(f"OrganizationUser with id {instructor_id} does not have instructor role.")
                CourseInstructor.objects.create(course=course, org_user=org_user)
        if self.image:
            course.replace_image(self.image)
        if self.target_audience:
            course.target_audience = self.target_audience
        if self.external_references:
            course.save()  # Save course before adding external references
            for ref in self.external_references:
                course.external_references.create(name=ref["name"], url=ref["url"])
        return course


class UpdateCourseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(None, min_length=1, examples=["Introduction to Python"])
    description: Optional[str] = Field(None, examples=["A beginner's course on Python programming."])
    imap_connection_id: Optional[int] = Field(None, examples=[1])
    newsletter_id: Optional[int] = Field(None, examples=[1])
    enabled: Optional[bool] = Field(None, examples=[True])
    reset_imap_connection: Optional[bool] = Field(None, examples=[False])
    reset_newsletter: Optional[bool] = Field(None, examples=[False])
    image: Optional[str] = Field(None, examples=["/path/to/course_image.png"])
    language: Optional[str] = Field(None, min_length=2, max_length=10, examples=["en"])
    target_audience: Optional[str] = Field(None, examples=["Beginners with no prior programming experience."])
    external_references: Optional[list[dict[str, str]]] = Field(
        None,
        examples=[
            [
                {
                    "name": "GitHub Repository",
                    "url": "https://github.com/AvaCodeSolutions/django-email-learning",
                },
                {
                    "name": "Documentation",
                    "url": "https://django-email-learning.readthedocs.io/",
                },
            ]
        ],
    )
    is_public: Optional[bool] = Field(None, examples=[True])
    send_certificate: Optional[bool] = Field(None, examples=[True])
    instructors: Optional[list[int]] = Field(None, examples=[1, 2, 3])

    @field_validator("description", "target_audience")
    @classmethod
    def strip_html_markup(cls, value: Optional[str]) -> Optional[str]:
        return strip_html(value) if value else value

    def to_django_model(self, course_id: int, organization_id: int) -> Course:
        try:
            course = Course.objects.get(id=course_id, organization_id=organization_id)
        except Course.DoesNotExist:
            raise ValueError(f"Course with id {course_id} does not exist.")
        if self.reset_imap_connection and self.imap_connection_id is not None:
            raise ValueError("Cannot set imap_connection_id when reset_imap_connection is True.")

        if self.title is not None:
            course.title = self.title
        if self.description is not None:
            course.description = self.description
        if self.imap_connection_id is not None:
            imap_connection = ImapConnection.objects.get(id=self.imap_connection_id)
            course.imap_connection = imap_connection
        if self.enabled is not None:
            if self.enabled and not CourseContent.objects.filter(course=course).exists():
                raise ValueError("Cannot enable a course that has no content.")
            course.enabled = self.enabled
        if self.reset_imap_connection:
            course.imap_connection = None
        if self.newsletter_id is not None:
            course.newsletter = Newsletter.objects.get(id=self.newsletter_id)
        if self.reset_newsletter:
            course.newsletter = None
        if self.image is not None:
            if self.image != "SKIP":
                course.replace_image(self.image)
        if not self.image:
            course.image = None
        if self.language is not None:
            course.language = self.language
        if self.target_audience is not None:
            course.target_audience = self.target_audience
        if self.external_references is not None:
            course.save()  # Save course before adding external references
            course.external_references.all().delete()
            for ref in self.external_references:
                course.external_references.create(name=ref["name"], url=ref["url"])
        if self.is_public is not None:
            course.is_public = self.is_public
        if self.send_certificate is not None:
            course.send_certificate = self.send_certificate
        if self.instructors is not None:
            instructors_to_remove = course.instructors.exclude(org_user_id__in=self.instructors)
            for instructor in instructors_to_remove:
                instructor.delete()
            instructors_to_add = set(self.instructors) - set(course.instructors.values_list("org_user_id", flat=True))
            for instructor_id in instructors_to_add:
                try:
                    org_user = OrganizationUser.objects.get(id=instructor_id, organization=course.organization)
                except OrganizationUser.DoesNotExist:
                    raise ValueError(
                        f"OrganizationUser with id {instructor_id} does not exist"
                        f" in organization {course.organization.name}."
                    )
                if not org_user.can_act_as_instructor():
                    raise ValueError(f"OrganizationUser with id {instructor_id} does not have instructor role.")
                CourseInstructor.objects.create(course=course, org_user=org_user)
        return course


class CourseResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str]
    organization_id: int
    imap_connection_id: Optional[int]
    newsletter_id: Optional[int] = None
    enabled: bool
    enrollments_count: dict[str, int]
    image: Optional[str] = None
    image_path: Optional[str] = None
    language: str
    is_rtl: bool = False
    target_audience: Optional[str] = None
    external_references: Optional[list[dict[str, str]]] = None
    is_public: bool
    send_certificate: bool
    instructors: Optional[list[InstructorResponse]] = None

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_django_model(course: Course, abs_url_builder: Callable) -> "CourseResponse":
        language_info = get_language_info(course.language)
        return CourseResponse.model_validate(
            {
                "id": course.id,
                "title": course.title,
                "slug": course.slug,
                "description": course.description,
                "organization_id": course.organization.id,
                "imap_connection_id": course.imap_connection.id if course.imap_connection else None,
                "newsletter_id": course.newsletter_id,
                "enabled": course.enabled,
                "enrollments_count": course.enrollments_count,
                "image": abs_url_builder(course.image.url) if course.image else None,
                "image_path": course.image.name if course.image else None,
                "language": course.language,
                "is_rtl": language_info["bidi"],
                "target_audience": course.target_audience,
                "external_references": [{"name": ref.name, "url": ref.url} for ref in course.external_references.all()]
                if course.external_references.exists()
                else None,
                "is_public": course.is_public,
                "send_certificate": course.send_certificate,
                "instructors": [
                    InstructorResponse(
                        display_name=instructor.org_user.display_name or instructor.org_user.user.email,
                        photo=instructor.org_user.photo.name if instructor.org_user.photo else None,
                    )
                    for instructor in course.instructors.all()
                ],
            }
        )


class CreateCourseContentRequest(BaseModel):
    priority: int | None = Field(gt=0, examples=[1], default=None)
    waiting_period: WaitingPeriod
    content: LessonCreate | QuizCreate | AssignmentCreate = Field(discriminator="type")

    @property
    def required_priority(self) -> int:
        if self.priority is not None:
            return self.priority
        else:
            raise ValueError("Priority must be set before converting to Django model.")

    def to_django_model(self, course: Course) -> CourseContent:
        lesson = None
        quiz = None
        assignment = None
        if isinstance(self.content, LessonCreate):
            lesson = Lesson(
                title=self.content.title,
                content=self.content.content,
            )
            lesson.save()
            content_type = CourseContentType.LESSON

        elif isinstance(self.content, AssignmentCreate):
            from django_email_learning.models import Assignment

            assignment = Assignment(
                title=self.content.title,
                description=self.content.description,
                is_blocking=self.content.is_blocking,  # type: ignore[misc]
                deadline_days=self.content.deadline_days,  # type: ignore[misc]
                requires_text_submission=self.content.requires_text_submission,  # type: ignore[misc]
                requires_file_submission=self.content.requires_file_submission,  # type: ignore[misc]
                reminder_interval_days=self.content.reminder_interval_days,  # type: ignore[misc]
            )
            assignment.save()
            content_type = CourseContentType.ASSIGNMENT

        elif isinstance(self.content, QuizCreate):
            quiz = Quiz(
                title=self.content.title,
                required_score=self.content.required_score,
                selection_strategy=self.content.selection_strategy.value,  # type: ignore[misc]
                deadline_days=self.content.deadline_days,  # type: ignore[misc]
                limited_attempts=self.content.limited_attempts,  # type: ignore[misc]
                is_blocking=self.content.is_blocking,  # type: ignore[misc]
                reminder_interval_days=self.content.reminder_interval_days,  # type: ignore[misc]
            )
            quiz.save()
            for question_data in self.content.questions:
                question = Question(
                    text=question_data.text,
                    priority=question_data.priority,
                    quiz=quiz,
                )
                question.save()
                for answer_data in question_data.answers:
                    answer = Answer(
                        text=answer_data.text,
                        is_correct=answer_data.is_correct,
                        question=question,
                    )
                    answer.save()
            content_type = CourseContentType.QUIZ

        course_content = CourseContent.objects.create(
            course=course,
            priority=self.required_priority,
            waiting_period=self.waiting_period.to_seconds(),
            assignment=assignment,
            lesson=lesson,
            quiz=quiz,
            type=content_type,
        )

        return course_content


class UpdateCourseContentRequest(BaseModel):
    priority: Optional[int] = Field(gt=0, examples=[1], default=None)
    waiting_period: Optional[WaitingPeriod] = None
    lesson: Optional[LessonUpdate] = None
    quiz: Optional[UpdateQuiz] = None
    assignment: Optional[AssignmentUpdate] = None
    is_published: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_at_least_one(self) -> "UpdateCourseContentRequest":
        # Check if all fields are None
        fields = [
            self.priority,
            self.waiting_period,
            self.lesson,
            self.quiz,
            self.assignment,
            self.is_published,
        ]
        if not any(f is not None for f in fields):
            raise ValueError(
                "At least one of 'priority', 'waiting_period', 'lesson', 'quiz',"
                " 'assignment', or 'is_published' must be provided."
            )
        return self


class CourseContentResponse(BaseModel):
    id: int
    priority: int
    waiting_period: int
    type: str
    lesson: Optional[LessonResponse] = None
    quiz: Optional[QuizResponse] = None
    assignment: Optional[AssignmentResponse] = None
    is_published: bool

    @field_serializer("waiting_period")
    def serialize_waiting_period(self, waiting_period: int) -> dict:
        return WaitingPeriod.from_seconds(waiting_period).model_dump()

    model_config = ConfigDict(from_attributes=True)


class CourseContentSummaryResponse(BaseModel):
    id: int
    title: str
    priority: int
    waiting_period: int
    is_published: bool
    type: str
    limited_attempts: Optional[bool] = None
    is_blocking: Optional[bool] = None

    @field_serializer("waiting_period")
    def serialize_waiting_period(self, waiting_period: int) -> dict:
        return WaitingPeriod.from_seconds(waiting_period).model_dump()

    model_config = ConfigDict(from_attributes=True)


class ReorderCourseContentsRequest(BaseModel):
    ordered_content_ids: list[int] = Field(min_length=2, examples=[[3, 1, 2]])
