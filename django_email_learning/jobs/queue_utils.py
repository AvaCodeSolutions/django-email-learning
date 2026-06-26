from typing import Callable, TypeVar

from django.conf import settings
from django.utils.module_loading import import_string

T = TypeVar("T")


def resolve_queue(settings_key: str, default_factory: Callable[[], T]) -> T:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    try:
        cls_or_obj = import_string(conf[settings_key])
        return cls_or_obj() if isinstance(cls_or_obj, type) else cls_or_obj
    except KeyError:
        return default_factory()
