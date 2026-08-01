import logging
from io import StringIO
from typing import Protocol

from django.core.management import call_command
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from django_email_learning.decorators import check_api_key
from django_email_learning.error_responses import UNEXPECTED_ERROR_MESSAGE
from django_email_learning.jobs.check_imap_job import CheckIMAPJob
from django_email_learning.jobs.deactivate_inactive_enrollments_job import (
    DeactivateInactiveEnrollmentsJob,
)
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.jobs.executor_utils import resolve_executor
from django_email_learning.jobs.send_newsletters_job import SendNewslettersJob
from django_email_learning.jobs.send_reminders_job import SendRemindersJob
from django_email_learning.models import JobExecution, JobName, JobStatus
from django_email_learning.ports.job_executor_protocol import JobExecutorProtocol
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)


def _get_job_executor() -> JobExecutorProtocol:
    from django_email_learning.services.defaults.thread_pool_job_executor import (
        ThreadPoolJobExecutor,
    )

    return resolve_executor(ThreadPoolJobExecutor)


executor: JobExecutorProtocol = _get_job_executor()


class TriggerableJob(Protocol):
    def start(self) -> JobExecution | None:
        ...


def _last_running_execution(job_name: str) -> JobExecution | None:
    return (
        JobExecution.objects.filter(job_name=job_name, status=JobStatus.RUNNING.value).order_by("-started_at").first()
    )


def _trigger_job(job: TriggerableJob, job_name: str, human_name: str) -> JsonResponse:
    job_execution = job.start()
    if job_execution is None:
        running = _last_running_execution(job_name)
        return JsonResponse(
            {
                "status": f"{human_name} already running",
                "job_execution_id": running.id if running else None,
            },
            status=409,
        )

    try:
        executor.submit(job_name=job_name, job_execution_id=job_execution.id)
    except Exception as e:
        job_execution.status = JobStatus.FAILED.value
        job_execution.error = str(e)
        job_execution.finished_at = timezone.now()
        job_execution.save()
        metric_service.job_execution_failed(job_name=job_name)
        # The detail stays on job_execution.error above, retrievable through
        # JobExecutionStatusView, rather than being echoed back in this 500.
        logger.exception("Triggering %s failed: %s", human_name, e.__class__.__name__)
        return JsonResponse(
            {"status": f"{human_name} failed", "error": UNEXPECTED_ERROR_MESSAGE},
            status=500,
        )

    return JsonResponse(
        {"status": f"{human_name} triggered", "job_execution_id": job_execution.id},
        status=202,
    )


@method_decorator(check_api_key(), name="get")
class DeliverContentsJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return _trigger_job(DeliverContentsJob(), JobName.DELIVER_CONTENTS.value, "DeliverContentsJob")


@method_decorator(check_api_key(), name="get")
class CheckIMAPJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return _trigger_job(CheckIMAPJob(), JobName.CHECK_IMAP.value, "CheckIMAPJob")


@method_decorator(check_api_key(), name="get")
class SendQuizRemindersJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return _trigger_job(SendRemindersJob(), JobName.SEND_REMINDERS.value, "SendRemidersJob")


@method_decorator(check_api_key(), name="get")
class DeactivateInactiveEnrollmentsJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return _trigger_job(
            DeactivateInactiveEnrollmentsJob(),
            JobName.DEACTIVATE_ENROLLMENTS.value,
            "DeactivateInactiveEnrollmentsJob",
        )


@method_decorator(check_api_key(), name="get")
class SendNewslettersJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        return _trigger_job(SendNewslettersJob(), JobName.SEND_NEWSLETTERS.value, "SendNewslettersJob")


@method_decorator(check_api_key(), name="get")
class JobExecutionStatusView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            job_execution = JobExecution.objects.get(id=kwargs["job_execution_id"])
        except JobExecution.DoesNotExist:
            return JsonResponse({"error": "Job execution not found"}, status=404)

        return JsonResponse(
            {
                "job_execution_id": job_execution.id,
                "job_name": job_execution.job_name,
                "status": job_execution.status,
                "started_at": job_execution.started_at.isoformat(),
                "finished_at": job_execution.finished_at.isoformat() if job_execution.finished_at else None,
                "error": UNEXPECTED_ERROR_MESSAGE if job_execution.error else None,
            },
            status=200,
        )


@method_decorator(check_api_key(), name="get")
class CleanupJobExecutionsView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            days = request.GET.get("days")
            dry_run = request.GET.get("dry_run", "false").lower() in {
                "1",
                "true",
                "yes",
            }

            command_stdout = StringIO()
            command_kwargs = {
                "dry_run": dry_run,
                "stdout": command_stdout,
            }
            if days is not None:
                command_kwargs["days"] = int(days)

            call_command("cleanup_job_executions", **command_kwargs)
            return JsonResponse(
                {
                    "status": "CleanupJobExecutions command triggered",
                    "output": command_stdout.getvalue().strip(),
                },
                status=202,
            )
        except ValueError:
            return JsonResponse(
                {"status": "CleanupJobExecutions failed", "error": "Invalid days"},
                status=400,
            )
        except Exception as e:
            metric_service.job_execution_failed(job_name="cleanup_job_executions")
            logger.exception("CleanupJobExecutions failed: %s", e.__class__.__name__)
            return JsonResponse(
                {
                    "status": "CleanupJobExecutions failed",
                    "error": UNEXPECTED_ERROR_MESSAGE,
                },
                status=500,
            )
