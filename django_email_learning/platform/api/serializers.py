import re
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)
from datetime import datetime
from django.utils import timezone
from typing import Optional, Literal, Any, Callable
from django.urls import reverse
from django_email_learning.models import (
    ApiKey,
    AssignmentSubmission,
    ContentDelivery,
    CourseInstructor,
    DeliveryStatus,
    Organization,
    ImapConnection,
    InboxFolder,
    Assignment,
    Lesson,
    Quiz,
    Question,
    Answer,
    CourseContent,
    Course,
    QuizSelectionStrategy,
    CourseContentType,
    Enrollment,
    EnrollmentStatus,
    OrganizationUser,
)
from django_email_learning.services.jwt_service import generate_jwt
from django_email_learning.services.storage_tools import (
    move_file,
    FileDoesNotExistError,
)
from django.utils.translation import get_language_info
import enum


class ApiKeyResponse(BaseModel):
    id: int
    key: str
    created_at: datetime
    created_by: Optional[str] = None

    @staticmethod
    def from_django_model(api_key: ApiKey) -> "ApiKeyResponse":
        decrypted_key = api_key.decrypt_password(api_key.key)
        salt = api_key.salt
        jwt_key = generate_jwt(
            {"key": decrypted_key, "salt": salt},
            exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()),
        )

        return ApiKeyResponse.model_validate(
            {
                "id": api_key.id,  # type: ignore[attr-defined]
                "key": jwt_key,
                "created_at": api_key.created_at,
                "created_by": api_key.created_by.username
                if api_key.created_by
                else None,
            }
        )


class GetOrCreateUserRequest(BaseModel):
    email: str = Field(min_length=1, examples=["user@example.com"])
    organization_id: int = Field(gt=0, examples=[1])

    @field_validator("email")
    def validate_email(cls, email: str) -> str:
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email):
            raise ValueError("Invalid email format")
        return email


class CreateEnrollmentRequest(BaseModel):
    learner_email: str = Field(min_length=1, examples=["user@example.com"])


class UserResponse(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)


class Identifier(BaseModel):
    id: int


class CreateCourseRequest(BaseModel):
    title: str = Field(min_length=1, examples=["Introduction to Python"])
    slug: str = Field(
        min_length=1,
        examples=["intro-to-python"],
        description="A short label for the course, used in URLs or email interactive actions. "
        "You can not edit it later.",
    )
    description: Optional[str] = Field(
        None, examples=["A beginner's course on Python programming."]
    )
    imap_connection_id: Optional[int] = Field(None, examples=[1])
    image: Optional[str] = Field(None, examples=["/path/to/course_image.png"])
    language: str = Field(min_length=2, max_length=10, examples=["en"])
    target_audience: Optional[str] = Field(
        None, examples=["Beginners with no prior programming experience."]
    )
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

    def to_django_model(self, organization_id: int) -> Course:
        organization = Organization.objects.get(id=organization_id)
        if not organization:
            raise ValueError(f"Organization with id {organization_id} does not exist.")
        imap_connection = None
        if self.imap_connection_id:
            try:
                imap_connection = ImapConnection.objects.get(
                    id=self.imap_connection_id, organization=organization
                )
            except ImapConnection.DoesNotExist:
                raise ValueError(
                    f"ImapConnection with id {self.imap_connection_id} does not exist."
                )
            imap_connection = ImapConnection.objects.get(
                id=self.imap_connection_id, organization=organization
            )
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
        if self.instructors:
            course.save()  # Save course before adding instructors
            for instructor_id in self.instructors:
                try:
                    org_user = OrganizationUser.objects.get(
                        id=instructor_id, organization=organization
                    )
                except OrganizationUser.DoesNotExist:
                    raise ValueError(
                        f"OrganizationUser with id {instructor_id} does not exist in organization {organization.name}."
                    )
                if not org_user.can_act_as_instructor():
                    raise ValueError(
                        f"OrganizationUser with id {instructor_id} does not have instructor role."
                    )
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
    title: Optional[str] = Field(
        None, min_length=1, examples=["Introduction to Python"]
    )
    description: Optional[str] = Field(
        None, examples=["A beginner's course on Python programming."]
    )
    imap_connection_id: Optional[int] = Field(None, examples=[1])
    enabled: Optional[bool] = Field(None, examples=[True])
    reset_imap_connection: Optional[bool] = Field(None, examples=[False])
    image: Optional[str] = Field(None, examples=["/path/to/course_image.png"])
    language: Optional[str] = Field(None, min_length=2, max_length=10, examples=["en"])
    target_audience: Optional[str] = Field(
        None, examples=["Beginners with no prior programming experience."]
    )
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

    def to_django_model(self, course_id: int) -> Course:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise ValueError(f"Course with id {course_id} does not exist.")
        if self.reset_imap_connection and self.imap_connection_id is not None:
            raise ValueError(
                "Cannot set imap_connection_id when reset_imap_connection is True."
            )

        if self.title is not None:
            course.title = self.title
        if self.description is not None:
            course.description = self.description
        if self.imap_connection_id is not None:
            imap_connection = ImapConnection.objects.get(id=self.imap_connection_id)
            course.imap_connection = imap_connection
        if self.enabled is not None:
            course.enabled = self.enabled
        if self.reset_imap_connection:
            course.imap_connection = None
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
            instructors_to_remove = course.instructors.exclude(
                org_user_id__in=self.instructors
            )
            for instructor in instructors_to_remove:
                instructor.delete()
            instructors_to_add = set(self.instructors) - set(
                course.instructors.values_list("org_user_id", flat=True)
            )
            for instructor_id in instructors_to_add:
                try:
                    org_user = OrganizationUser.objects.get(
                        id=instructor_id, organization=course.organization
                    )
                except OrganizationUser.DoesNotExist:
                    raise ValueError(
                        f"OrganizationUser with id {instructor_id} does not exist in organization {course.organization.name}."
                    )
                if not org_user.can_act_as_instructor():
                    raise ValueError(
                        f"OrganizationUser with id {instructor_id} does not have instructor role."
                    )
                CourseInstructor.objects.create(course=course, org_user=org_user)
        return course


class InstructorResponse(BaseModel):
    display_name: str
    photo: Optional[str] = None


class CourseResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str]
    organization_id: int
    imap_connection_id: Optional[int]
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
    def from_django_model(
        course: Course, abs_url_builder: Callable
    ) -> "CourseResponse":
        language_info = get_language_info(course.language)
        return CourseResponse.model_validate(
            {
                "id": course.id,
                "title": course.title,
                "slug": course.slug,
                "description": course.description,
                "organization_id": course.organization.id,
                "imap_connection_id": course.imap_connection.id
                if course.imap_connection
                else None,
                "enabled": course.enabled,
                "enrollments_count": course.enrollments_count,
                "image": abs_url_builder(course.image.url) if course.image else None,
                "image_path": course.image.name if course.image else None,
                "language": course.language,
                "is_rtl": language_info["bidi"],
                "target_audience": course.target_audience,
                "external_references": [
                    {"name": ref.name, "url": ref.url}
                    for ref in course.external_references.all()
                ]
                if course.external_references.exists()
                else None,
                "is_public": course.is_public,
                "send_certificate": course.send_certificate,
                "instructors": [
                    InstructorResponse(
                        display_name=instructor.org_user.display_name
                        or instructor.org_user.user.email,
                        photo=instructor.org_user.photo.name
                        if instructor.org_user.photo
                        else None,
                    )
                    for instructor in course.instructors.all()
                ],
            }
        )


class CourseSummaryResponse(BaseModel):
    id: int
    title: str
    slug: str
    is_public: bool

    model_config = ConfigDict(from_attributes=True)


class CreateImapConnectionRequest(BaseModel):
    email: str = Field(min_length=1, examples=["user@example.com"])
    password: str = Field(min_length=1, examples=["aSafePassword123!"])
    server: str = Field(min_length=1, examples=["imap.example.com"])
    port: int = Field(gt=0, examples=[993])
    folders: list[str] = Field(min_length=1, examples=[["inbox"]])

    @field_validator("folders", mode="after")
    def validate_folders(cls, v: list[str]) -> list[str]:
        if "inbox" not in v:
            raise ValueError("Folders list must contain 'inbox'.")
        return v

    def to_django_model(self, organization_id: int) -> ImapConnection:
        organization = Organization.objects.get(id=organization_id)
        if not organization:
            raise ValueError(f"Organization with id {organization_id} does not exist.")
        imap_connection = ImapConnection(
            email=self.email,
            password=self.password,
            server=self.server,
            port=self.port,
            organization=organization,
        )
        imap_connection.save()
        for folder in self.folders:
            InboxFolder.objects.create(
                imap_connection=imap_connection, folder_name=folder
            )
        return imap_connection


class ImapConnectionResponse(BaseModel):
    id: int
    email: str
    server: str
    port: int
    organization_id: int
    folders: Any

    @field_serializer("folders")
    def serialize_folders(self, folders: Any) -> list[str]:
        return [folder.folder_name for folder in folders.all()]  # type: ignore[attr-defined]

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None
    logo_path: Optional[str] = None
    description: Optional[str] = None
    public_url: str
    website: Optional[str] = None
    youtube_channel: Optional[str] = None
    linkedin_page: Optional[str] = None
    is_public: bool

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_django_model(
        organization: Organization, abs_url_builder: Callable
    ) -> "OrganizationResponse":
        url = reverse(
            "django_email_learning:public:organization_view",
            kwargs={"organization_id": organization.id},
        )
        return OrganizationResponse.model_validate(
            {
                "id": organization.id,
                "name": organization.name,
                "logo": abs_url_builder(organization.logo.url)
                if organization.logo
                else None,
                "logo_path": organization.logo.name if organization.logo else None,
                "description": organization.description,
                "public_url": abs_url_builder(url),
                "website": organization.website,
                "youtube_channel": organization.youtube_channel,
                "linkedin_page": organization.linkedin_page,
                "is_public": organization.is_public,
            }
        )


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, examples=["AvaCode"])
    description: Optional[str] = Field(
        None, examples=["A description of the organization."]
    )
    logo: Optional[str] = Field(None, examples=["/path/to/logo.png"])
    website: Optional[str] = Field(None, examples=["https://example.com"])
    youtube_channel: Optional[str] = Field(
        None, examples=["https://youtube.com/channel/xyz"]
    )
    linkedin_page: Optional[str] = Field(
        None, examples=["https://linkedin.com/company/xyz"]
    )
    is_public: bool = Field(default=True, examples=[True])

    def to_django_model(self) -> Organization:
        organization = Organization(
            name=self.name,
            description=self.description,
            website=self.website,
            youtube_channel=self.youtube_channel,
            linkedin_page=self.linkedin_page,
            is_public=self.is_public,
        )
        organization.save()
        organization.refresh_from_db()
        if self.logo:
            try:
                allowed_extensions = [".jpg", ".jpeg", ".png", ".svg"]
                if not any(
                    self.logo.lower().endswith(ext) for ext in allowed_extensions
                ):
                    raise ValueError(
                        "Logo must be an image file with a valid extension."
                    )
                final_path = move_file(
                    self.logo,
                    f"organization_logos/{organization.id}/{self.logo.split('/')[-1]}",
                )
                organization.logo = final_path
                organization.save()
            except FileDoesNotExistError:
                raise ValueError("Logo file does not exist.")

        return organization


class UpdateOrganizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, min_length=1, examples=["AvaCode"])
    description: Optional[str] = Field(
        None, examples=["A description of the organization."]
    )
    website: Optional[str] = Field(None, examples=["https://example.com"])
    youtube_channel: Optional[str] = Field(
        None, examples=["https://youtube.com/channel/xyz"]
    )
    linkedin_page: Optional[str] = Field(
        None, examples=["https://linkedin.com/company/xyz"]
    )
    logo: Optional[str] = Field(None, examples=["/path/to/logo.png"])
    remove_logo: Optional[bool] = Field(None, examples=[True])
    is_public: Optional[bool] = Field(None, examples=[True])


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    INSTRUCTOR = "instructor"
    VIEWER = "viewer"


class AddOrganizationUserRequest(BaseModel):
    user_id: int = Field(gt=0, examples=[1])
    role: UserRole = Field(min_length=1, examples=[UserRole.ADMIN])
    display_name: Optional[str] = Field(None, examples=["John Doe"])
    photo: Optional[str] = Field(None, examples=["/path/to/photo.png"])

    @model_validator(mode="before")
    def validate_instructor_display_name(cls, values: dict) -> dict:
        role = values.get("role")
        display_name = values.get("display_name")
        if role == UserRole.INSTRUCTOR and not display_name:
            raise ValueError("Instructor role requires a display name.")
        return values


class UpdateOrganizationUserRequest(BaseModel):
    role: UserRole = Field(min_length=1, examples=[UserRole.ADMIN])
    display_name: Optional[str] = Field(None, examples=["John Doe"])
    photo: Optional[str] = Field(None, examples=["/path/to/photo.png"])

    @model_validator(mode="before")
    def validate_instructor_display_name(cls, values: dict) -> dict:
        role = values.get("role")
        display_name = values.get("display_name")
        if role == UserRole.INSTRUCTOR and not display_name:
            raise ValueError("Instructor role requires a display name.")
        return values


class OrganizationUserResponse(BaseModel):
    id: int
    user_id: int
    organization_id: int
    email: str
    role: UserRole
    can_act_as_instructor: bool
    display_name: Optional[str] = None
    photo: Optional[str] = None
    photo_url: Optional[str] = None

    @staticmethod
    def from_django_model(
        org_user: OrganizationUser, request: Any
    ) -> "OrganizationUserResponse":
        return OrganizationUserResponse(
            id=org_user.id,
            user_id=org_user.user.id,
            organization_id=org_user.organization.id,
            email=org_user.user.email,
            role=UserRole(org_user.role),
            can_act_as_instructor=org_user.can_act_as_instructor(),
            display_name=org_user.display_name,
            photo=org_user.photo.name if org_user.photo else None,
            photo_url=request.build_absolute_uri(org_user.photo.url)
            if org_user.photo
            else None,
        )


class UpdateSessionRequest(BaseModel):
    active_organization_id: int = Field(examples=[1])

    model_config = ConfigDict(extra="forbid")


class SessionInfo(BaseModel):
    active_organization_id: int

    @classmethod
    def populate_from_session(cls, session):  # type: ignore[no-untyped-def]
        return super().model_validate(
            {"active_organization_id": session.get("active_organization_id")}
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


class LessonCreate(BaseModel):
    title: str
    content: str
    type: Literal["lesson"] = "lesson"


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class LessonResponse(BaseModel):
    id: int
    title: str
    content: str

    model_config = ConfigDict(from_attributes=True)


class AnswerCreate(BaseModel):
    text: str
    is_correct: bool = Field(examples=[True])


class AnswerUpdate(AnswerCreate):
    id: Optional[int] = None


class AnswerObject(BaseModel):
    id: int
    text: str
    is_correct: bool

    model_config = ConfigDict(from_attributes=True)


class QuestionCreate(BaseModel):
    text: str
    priority: int = Field(gt=0, examples=[1])
    answers: list[AnswerCreate] = Field(min_length=2)

    @field_validator("answers")
    @classmethod
    def at_least_one_correct_answer(
        cls, answers: list[AnswerCreate]
    ) -> list[AnswerCreate]:
        correct_answers = [answer for answer in answers if answer.is_correct]
        if not correct_answers:
            raise ValueError("At least one answer must be marked as correct.")
        return answers


class QuestionUpdate(QuestionCreate):
    id: Optional[int] = None
    answers: list[AnswerUpdate] = Field(min_length=2)  # type: ignore[assignment]


class QuestionObject(BaseModel):
    id: int
    text: str
    priority: int
    answers: Any  # Will be converted to list in field_serializer

    @field_serializer("answers")
    def serialize_answers(self, answers: Any) -> list[dict]:
        return [
            AnswerObject.model_validate(answer).model_dump() for answer in answers.all()
        ]

    model_config = ConfigDict(from_attributes=True)


MIN_QUIZ_DEADLINE = 0  # Allow 0 to indicate no deadline


class UpdateQuiz(BaseModel):
    questions: Optional[list[QuestionUpdate]] = Field(min_length=1, default=None)
    title: Optional[str] = None
    required_score: Optional[int] = Field(ge=0, examples=[80], default=None)
    selection_strategy: Optional[QuizSelectionStrategy] = None
    limited_attempts: Optional[bool] = None
    deadline_days: Optional[int] = Field(
        ge=MIN_QUIZ_DEADLINE, examples=[14], default=None
    )
    is_blocking: Optional[bool] = None
    reminder_interval_days: Optional[int] = Field(default=None, examples=[3])

    model_config = ConfigDict(extra="forbid")


class QuizCreate(BaseModel):
    title: str
    required_score: int = Field(ge=0, examples=[80])
    selection_strategy: QuizSelectionStrategy
    deadline_days: int = Field(ge=MIN_QUIZ_DEADLINE, examples=[14])
    questions: list[QuestionCreate] = Field(min_length=1)
    type: Literal["quiz"] = "quiz"
    limited_attempts: bool = Field(default=True, examples=[True])
    is_blocking: bool = Field(default=True, examples=[True])
    reminder_interval_days: Optional[int] = Field(default=None, examples=[3])


class QuizResponse(BaseModel):
    id: int
    title: str
    required_score: int
    selection_strategy: str
    deadline_days: int = Field(ge=MIN_QUIZ_DEADLINE)
    questions: Any  # Will be converted to list in field_serializer
    limited_attempts: bool
    is_blocking: bool
    reminder_interval_days: Optional[int] = None

    @field_serializer("questions")
    def serialize_questions(self, questions: Any) -> list[dict]:
        return [
            QuestionObject.model_validate(question).model_dump()
            for question in questions.all()
        ]

    model_config = ConfigDict(from_attributes=True)


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
            raise ValueError(
                f"Cannot convert {seconds} seconds to a valid WaitingPeriod."
            )


class EnrollmentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_title: str
    status: EnrollmentStatus
    progress: int
    certificate_url: str | None = None


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


class ReviewResult(enum.StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUESTING_CHANGES = "requesting_changes"


class ReviewRquest(BaseModel):
    review_result: ReviewResult
    comment: Optional[str] = None


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


class GroupEnrollmentRequest(BaseModel):
    groups: list[str] = Field(
        min_length=1, default=["all"], examples=[["group1", "group2"]]
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
                "At least one of 'priority', 'waiting_period', 'lesson', 'quiz', 'assignment', or 'is_published' must be provided."
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
                display_name=submission.reviewer.display_name
                or submission.reviewer.user.email,  # type: ignore[union-attr]
                photo=request.build_absolute_uri(submission.reviewer.photo.url)
                if submission.reviewer.photo
                else None,
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
            reviewed_by=submission.reviewer.display_name
            if submission.reviewer
            else None,  # type: ignore[union-attr]
        )


class NewsletterResponse(BaseModel):
    id: int
    title: str
    language: str
    organization_id: int
    subscriber_count: int

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_django_model(newsletter: Any) -> "NewsletterResponse":
        return NewsletterResponse(
            id=newsletter.id,
            title=newsletter.title,
            language=newsletter.language,
            organization_id=newsletter.organization_id,
            subscriber_count=newsletter.subscribers.count(),
        )


class CreateNewsletterRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    language: str = Field(min_length=2, max_length=10)

    def to_django_model(self, organization_id: int) -> Any:
        from django_email_learning.models import Newsletter

        return Newsletter(
            title=self.title,
            language=self.language,
            organization_id=organization_id,
        )


class SendoutResponse(BaseModel):
    id: int
    subject: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    status: str
    retry_count: int

    model_config = ConfigDict(from_attributes=True)


class CreateSendoutRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    scheduled_at: datetime


class UpdateSendoutRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    scheduled_at: datetime


class SendoutDetailResponse(BaseModel):
    id: int
    subject: str
    body: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    status: str
    retry_count: int

    model_config = ConfigDict(from_attributes=True)
