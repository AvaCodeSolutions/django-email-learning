from pydantic import BaseModel, Field

from .language_models import LanguageModel


class EditTextRequest(BaseModel):
    input: str = Field(
        min_length=40,
        # This carries the selection's HTML markup, not just its plain text,
        # so it needs headroom above the frontend's 1000-char plain-text cap
        # for block tags (e.g. multiple <li>/<p>/<h2>) and entity expansion.
        max_length=2000,
        description="The input to be edited by the AI model.",
    )
    model: LanguageModel = Field(default=LanguageModel.GPT_5_NANO)
