from typing import Callable

from django.conf import settings
from django.utils.module_loading import import_string

from django_email_learning.ports.job_executor_protocol import JobExecutorProtocol


def resolve_executor(default_factory: Callable[[], JobExecutorProtocol]) -> JobExecutorProtocol:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    try:
        cls_or_obj = import_string(conf["JOB_EXECUTOR"])
        return cls_or_obj() if isinstance(cls_or_obj, type) else cls_or_obj
    except KeyError:
        return default_factory()
