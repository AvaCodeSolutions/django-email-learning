from typing import Callable, TypeVar

from django.conf import settings
from django.utils.module_loading import import_string

T = TypeVar("T")


def resolve_executor(default_factory: Callable[[], T]) -> T:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    try:
        cls_or_obj = import_string(conf["JOB_EXECUTOR"])
        return cls_or_obj() if isinstance(cls_or_obj, type) else cls_or_obj
    except KeyError:
        return default_factory()
