from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from django.utils import timezone

from django_email_learning.models import JobExecution, JobStatus

P = ParamSpec("P")
R = TypeVar("R")


def track_job_execution(
    *,
    metric_service: object,
    job_name: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(self: object, job_execution: JobExecution, *args: P.args, **kwargs: P.kwargs) -> R:  # type: ignore[misc]
            start_time = timezone.now()
            metric_service.job_execution_started(job_name=job_name)  # type: ignore[attr-defined]
            try:
                return func(self, job_execution, *args, **kwargs)  # type: ignore[arg-type]
            except Exception as e:
                job_execution.status = JobStatus.FAILED.value
                job_execution.error = str(e)
                job_execution.finished_at = timezone.now()
                job_execution.save()
                metric_service.job_execution_failed(job_name=job_name)  # type: ignore[attr-defined]
                raise
            finally:
                execution_time = int((timezone.now() - start_time).total_seconds())
                metric_service.job_execution_finished(  # type: ignore[attr-defined]
                    job_name=job_name,
                    execution_time=execution_time,
                )

        return wrapper  # type: ignore[return-value]

    return decorator
