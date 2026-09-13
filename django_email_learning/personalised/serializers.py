from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
)


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
        return [PublicAnswerSerializer.model_validate(answer).model_dump() for answer in answers.all()]


class PublicQuizSerializer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    questions: Any

    @field_serializer("questions")
    def serialize_questions(self, questions: Any) -> list[dict]:
        return [PublicQuestionSerializer.model_validate(question).model_dump() for question in questions.all()]


class PublicDecisionOptionSerializer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


class PublicDecisionSerializer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    prompt: str
    options: Any

    @field_serializer("options")
    def serialize_options(self, options: Any) -> list[dict]:
        return [PublicDecisionOptionSerializer.model_validate(option).model_dump() for option in options.all()]
