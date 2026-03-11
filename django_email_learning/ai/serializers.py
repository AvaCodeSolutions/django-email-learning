from pydantic import BaseModel, Field
from .language_models import LanguageModel


class EditTextRequest(BaseModel):
    input: str = Field(
        min_length=40,
        max_length=500,
        description="The input to be edited by the AI model.",
    )
    model: LanguageModel = Field(default=LanguageModel.GPT_5_NANO)
