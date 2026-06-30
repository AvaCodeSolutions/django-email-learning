from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from django.utils import timezone

P = ParamSpec("P")
R = TypeVar("R")


def track_job_execution(
    *,
    metric_service: object,
    job_name: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = timezone.now()
            metric_service.job_execution_started(job_name=job_name)  # type: ignore[attr-defined]
            try:
                return func(*args, **kwargs)
            finally:
                execution_time = int((timezone.now() - start_time).total_seconds())
                metric_service.job_execution_finished(  # type: ignore[attr-defined]
                    job_name=job_name,
                    execution_time=execution_time,
                )

        return wrapper

    return decorator
