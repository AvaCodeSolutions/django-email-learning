from enum import Enum
from .open_ai_adapter import OpenAiAdapter
from .ai_service_protocol import AiServiceProtocol


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

    GPT_4O_MINI = ("gpt-4o-mini", OpenAiAdapter)
    """OpenAI GPT-4o mini model (balanced quality and speed)."""

    GPT_5_NANO = ("gpt-5-nano", OpenAiAdapter)
    """OpenAI GPT-5 nano model (smallest and fastest GPT-5 variant)."""

    GPT_5_MINI = ("gpt-5-mini", OpenAiAdapter)
    """OpenAI GPT-5 mini model (higher quality than nano, still efficient)."""

    def __init__(self, model_name: str, adapter_class: type[AiServiceProtocol]) -> None:
        """Attach provider metadata to each model enum value.

        :param model_name: External model name used by the AI provider API.
        :param adapter_class: Adapter implementing :class:`AiServiceProtocol`.
        """
        self.model_name = model_name
        self.adapter_class = adapter_class
