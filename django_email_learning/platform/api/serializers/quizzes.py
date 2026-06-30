from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from django_email_learning.models import QuizSelectionStrategy

MIN_QUIZ_DEADLINE = 0  # Allow 0 to indicate no deadline


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
    def at_least_one_correct_answer(cls, answers: list[AnswerCreate]) -> list[AnswerCreate]:
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
        return [AnswerObject.model_validate(answer).model_dump() for answer in answers.all()]

    model_config = ConfigDict(from_attributes=True)


class UpdateQuiz(BaseModel):
    questions: Optional[list[QuestionUpdate]] = Field(min_length=1, default=None)
    title: Optional[str] = None
    required_score: Optional[int] = Field(ge=0, examples=[80], default=None)
    selection_strategy: Optional[QuizSelectionStrategy] = None
    limited_attempts: Optional[bool] = None
    deadline_days: Optional[int] = Field(ge=MIN_QUIZ_DEADLINE, examples=[14], default=None)
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
        return [QuestionObject.model_validate(question).model_dump() for question in questions.all()]

    model_config = ConfigDict(from_attributes=True)
