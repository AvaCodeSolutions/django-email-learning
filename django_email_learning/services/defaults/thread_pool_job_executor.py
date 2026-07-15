import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import close_old_connections

from django_email_learning.models import JobExecution

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
        try:
            job_execution = JobExecution.objects.get(id=job_execution_id)
            job_class = JOB_REGISTRY[job_name]
            job_class()._run_job(job_execution)
        except Exception:
            # track_job_execution already persisted the failure onto the
            # JobExecution row and emitted the metric before re-raising.
            logger.exception(f"Job {job_name} (execution {job_execution_id}) failed.")
