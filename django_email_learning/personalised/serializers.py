from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
)
from typing import Any


class PublicAnswerSerializer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


class PublicQuestionSerializer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    answers: Any

    @field_serializer("answers")
    def serialize_answers(self, answers: Any) -> list[dict]:
        return [
            PublicAnswerSerializer.model_validate(answer).model_dump()
            for answer in answers.all()
        ]


class PublicQuizSerializer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    questions: Any

    @field_serializer("questions")
    def serialize_questions(self, questions: Any) -> list[dict]:
        return [
            PublicQuestionSerializer.model_validate(question).model_dump()
            for question in questions.all()
        ]
