import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from django_email_learning.models import JobExecution, JobStatus
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)

DEFAULT_MAX_WORKERS = 4


def _get_max_workers() -> int:
    conf: dict = getattr(settings, "DJANGO_EMAIL_LEARNING", {})
    return int(conf.get("JOB_EXECUTOR_MAX_WORKERS", DEFAULT_MAX_WORKERS))


class ThreadPoolJobExecutor:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=_get_max_workers())

    def submit(self, job_name: str, job_execution_id: int) -> None:
        self._executor.submit(self._run, job_name, job_execution_id)

    def _run(self, job_name: str, job_execution_id: int) -> None:
        from django_email_learning.jobs.registry import JOB_REGISTRY

        # Each thread needs its own DB connection.
        close_old_connections()
        job_execution: JobExecution | None = None
        try:
            job_execution = JobExecution.objects.get(id=job_execution_id)
            job_class = JOB_REGISTRY[job_name]
            job_class()._run_job(job_execution)
        except Exception as e:
            logger.exception(f"Job {job_name} (execution {job_execution_id}) failed.")
            # If the failure happened inside _run_job, track_job_execution already
            # marked the row FAILED and emitted the metric. This branch only covers
            # failures before that point (lookup, registry, or job construction).
            if job_execution is not None and job_execution.status == JobStatus.RUNNING.value:
                job_execution.status = JobStatus.FAILED.value
                job_execution.error = str(e)
                job_execution.finished_at = timezone.now()
                job_execution.save()
                metric_service.job_execution_failed(job_name=job_name)
