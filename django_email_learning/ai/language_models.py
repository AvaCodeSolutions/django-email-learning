from enum import Enum

from .ai_service_protocol import AiServiceProtocol
from .open_ai_adapter import OpenAiAdapter


class LanguageModel(Enum):
    """Supported AI text-editing models.

    Each enum value maps to:

    - ``model_name``: The provider model identifier sent to the AI API.
    - ``adapter_class``: The adapter that knows how to call that provider.

    The project currently ships with OpenAI-backed models only.

    .. note::
       These models are used when
       ``DJANGO_EMAIL_LEARNING['AI']['TEXT_EDITING_MODEL']`` is configured.
       AI configuration is optional and only required when using AI editing
       features.
    """

    # Recommended models

    GPT_6_LUNA = ("gpt-6-luna", OpenAiAdapter)
    """OpenAI GPT-6 Luna model (efficient for focused, high-volume text tasks)."""

    GPT_6_1_TERRA = ("gpt-6.1-terra", OpenAiAdapter)
    """OpenAI GPT-6.1 Terra model (higher-quality text and reasoning)."""

    GPT_6_1_SOL = ("gpt-6.1-sol", OpenAiAdapter)
    """OpenAI GPT-6.1 Sol model (more capable reasoning for complex tasks)."""

    # Deprecated models kept for backward compatibility

    GPT_5_NANO = ("gpt-5-nano", OpenAiAdapter)
    """Deprecated: scheduled for shutdown on December 11, 2026."""

    GPT_5_MINI = ("gpt-5-mini", OpenAiAdapter)
    """Deprecated: scheduled for shutdown on December 11, 2026."""

    GPT_5 = ("gpt-5", OpenAiAdapter)
    """Deprecated: scheduled for shutdown on December 11, 2026."""

    GPT_4O_MINI = ("gpt-4o-mini", OpenAiAdapter)
    """Deprecated: scheduled for shutdown on January 14, 2027."""

    def __init__(self, model_name: str, adapter_class: type[AiServiceProtocol]) -> None:
        """Attach provider metadata to each model enum value.

        :param model_name: External model name used by the AI provider API.
        :param adapter_class: Adapter implementing :class:`AiServiceProtocol`.
        """
        self.model_name = model_name
        self.adapter_class = adapter_class
