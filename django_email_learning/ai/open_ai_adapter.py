import os

from django.conf import settings
from openai import OpenAI

from .ai_service_protocol import AiServiceProtocol

DJANGO_EMAIL_LEARNING_CONFIG = getattr(settings, "DJANGO_EMAIL_LEARNING", {})


class OpenAiAdapter(AiServiceProtocol):
    def __init__(self) -> None:
        API_KEY = DJANGO_EMAIL_LEARNING_CONFIG.get("AI", {}).get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        if not API_KEY:
            raise ValueError(
                "OpenAI API key is required. Please set it in Django settings or as an environment variable."
            )
        self._client = OpenAI(api_key=API_KEY)

    def edit_text(self, text: str, model: str) -> str:
        # Placeholder for OpenAI API integration
        response = self._client.responses.create(
            model=model,
            input=[
                {
                    "role": "developer",
                    "content": "You are a helpful assistant that edits text for grammar and clarity. The input is "
                    "one or more complete HTML block elements (e.g. <h2>, <p>, <ul>, <blockquote>). Preserve the "
                    "exact number and type of these block-level elements exactly as given: do not merge, split, "
                    "add, or remove blocks, and do not add any wrapper element around them. Only edit the text "
                    "inside each block. Return ONLY the edited HTML, with the same block tags.",
                },
                {"role": "user", "content": text},
            ],
            store=False,
        )
        return response.output_text
