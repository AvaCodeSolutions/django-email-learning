from pydantic import BaseModel, field_validator


class QuestionResponse(BaseModel):
    id: int
    answers: set[int]


class QuizSubmissionRequest(BaseModel):
    answers: list[QuestionResponse]
    token: str

    @field_validator("answers")
    def validate_answers(cls, v: list[QuestionResponse]) -> list[QuestionResponse]:
        question_ids = []
        for response in v:
            if response.id in question_ids:
                raise ValueError(f"Duplicate question ID found: {response.id}")
            question_ids.append(response.id)
        return v
