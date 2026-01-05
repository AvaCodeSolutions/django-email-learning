from pydantic import BaseModel


class QuestionResponse(BaseModel):
    id: int
    answers: list[int]


class QuizSubmissionRequest(BaseModel):
    answers: list[QuestionResponse]
    token: str
