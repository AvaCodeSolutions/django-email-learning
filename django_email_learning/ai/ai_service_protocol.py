from typing import Protocol


class AiServiceProtocol(Protocol):
    def edit_text(self, text: str, model: str) -> str: ...
