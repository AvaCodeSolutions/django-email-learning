from .ai_service_protocol import AiServiceProtocol
from openai import OpenAI
from django.conf import settings
import os


DJANGO_EMAIL_LEARNING_CONFIG = getattr(settings, "DJANGO_EMAIL_LEARNING", {})


class OpenAiAdapter(AiServiceProtocol):
    def __init__(self) -> None:
        API_KEY = DJANGO_EMAIL_LEARNING_CONFIG.get("AI", {}).get(
            "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")
        )
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
                    "content": "You are a helpful assistant that edits text for grammar and clarity. Preserve the existing HTML structure and tags when present. Do not add wrapper containers like <ul>, <ol>, or <p> unless they already exist in the input. Return ONLY the edited text.",
                },
                {"role": "user", "content": text},
            ],
            store=False,
        )
        return response.output_text
