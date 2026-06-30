from enum import StrEnum

from pydantic import BaseModel


class Display(StrEnum):
    INLINE = "inline"
    BLOCK = "block"
    INLINE_BLOCK = "inline-block"
    NONE = "none"


class WebComponent(BaseModel):
    script_url: str | None = None
    style_url: str | None = None
    html: str
    container_display: Display = Display.INLINE_BLOCK
