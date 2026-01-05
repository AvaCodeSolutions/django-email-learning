from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)
from typing import Optional, Literal, Any
from django_email_learning.models import (
    Organization,
    ImapConnection,
    Lesson,
    Quiz,
    Question,
    Answer,
    CourseContent,
    Course,
)
import enum


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
        )
        if imap_connection:
            course.imap_connection = imap_connection
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

        return course


class CourseResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str]
    organization_id: int
    imap_connection_id: Optional[int]
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class CreateImapConnectionRequest(BaseModel):
    email: str = Field(min_length=1, examples=["user@example.com"])
    password: str = Field(min_length=1, examples=["aSafePassword123!"])
    server: str = Field(min_length=1, examples=["imap.example.com"])
    port: int = Field(gt=0, examples=[993])

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
        return imap_connection


class ImapConnectionResponse(BaseModel):
    id: int
    email: str
    server: str
    port: int
    organization_id: int

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, examples=["AvaCode"])
    description: Optional[str] = Field(
        None, examples=["A description of the organization."]
    )

    def to_django_model(self) -> Organization:
        organization = Organization(name=self.name, description=self.description)
        return organization


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


class LessonCreate(BaseModel):
    title: str
    content: str
    type: Literal["lesson"]


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class LessonResponse(BaseModel):
    id: int
    title: str
    content: str
    is_published: bool

    model_config = ConfigDict(from_attributes=True)


class AnswerCreate(BaseModel):
    text: str
    is_correct: bool = Field(examples=[True])


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


class UpdateQuiz(BaseModel):
    questions: Optional[list[QuestionCreate]] = Field(min_length=1)
    title: Optional[str] = None
    required_score: Optional[int] = Field(ge=0, examples=[80], default=None)

    model_config = ConfigDict(extra="forbid")


class QuizCreate(BaseModel):
    title: str
    required_score: int = Field(ge=0, examples=[80])
    questions: list[QuestionCreate] = Field(min_length=1)
    type: Literal["quiz"]


class QuizResponse(BaseModel):
    id: int
    title: str
    required_score: int
    questions: Any  # Will be converted to list in field_serializer
    is_published: bool

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


class CreateCourseContentRequest(BaseModel):
    priority: int | None = Field(gt=0, examples=[1], default=None)
    waiting_period: WaitingPeriod
    content: LessonCreate | QuizCreate = Field(discriminator="type")

    @property
    def required_priority(self) -> int:
        if self.priority is not None:
            return self.priority
        else:
            raise ValueError("Priority must be set before converting to Django model.")

    def to_django_model(self, course: Course) -> CourseContent:
        lesson = None
        quiz = None
        if isinstance(self.content, LessonCreate):
            lesson = Lesson(
                title=self.content.title,
                content=self.content.content,
            )
            lesson.save()
            content_type = "lesson"
        elif isinstance(self.content, QuizCreate):
            quiz = Quiz(
                title=self.content.title,
                required_score=self.content.required_score,
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
            content_type = "quiz"
        course_content = CourseContent.objects.create(
            course=course,
            priority=self.required_priority,
            waiting_period=self.waiting_period.to_seconds(),
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
            self.is_published,
        ]
        if not any(f is not None for f in fields):
            raise ValueError(
                "At least one of 'priority', 'waiting_period', 'lesson', 'quiz', or 'is_published' must be provided."
            )
        return self


class CourseContentResponse(BaseModel):
    id: int
    priority: int
    waiting_period: int
    type: str
    lesson: Optional[LessonResponse] = None
    quiz: Optional[QuizResponse] = None

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

    @field_serializer("waiting_period")
    def serialize_waiting_period(self, waiting_period: int) -> dict:
        return WaitingPeriod.from_seconds(waiting_period).model_dump()

    model_config = ConfigDict(from_attributes=True)


class ReorderCourseContentsRequest(BaseModel):
    ordered_content_ids: list[int] = Field(min_length=2, examples=[[3, 1, 2]])
