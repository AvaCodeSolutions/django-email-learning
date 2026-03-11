from enum import Enum
from .open_ai_adapter import OpenAiAdapter
from .ai_service_protocol import AiServiceProtocol


class LanguageModel(Enum):
    GPT_4O_MINI = ("gpt-4o-mini", OpenAiAdapter)
    GPT_5_NANO = ("gpt-5-nano", OpenAiAdapter)
    GPT_5_MINI = ("gpt-5-mini", OpenAiAdapter)

    def __init__(self, model_name: str, adapter_class: type[AiServiceProtocol]) -> None:
        self.model_name = model_name
        self.adapter_class = adapter_class
