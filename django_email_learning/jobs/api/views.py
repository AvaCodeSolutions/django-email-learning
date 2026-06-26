from django.views import View
from django_email_learning.decorators import check_api_key
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.jobs.check_imap_job import CheckIMAPJob
from django_email_learning.jobs.send_newsletters_job import SendNewslettersJob
from django_email_learning.jobs.send_reminders_job import SendRemindersJob
from django_email_learning.jobs.deactivate_inactive_enrollments_job import (
    DeactivateInactiveEnrollmentsJob,
)
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.core.management import call_command
from io import StringIO

from django_email_learning.models import JobName
from django_email_learning.services.metrics_service import metric_service


@method_decorator(check_api_key(), name="get")
class DeliverContentsJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            job = DeliverContentsJob()
            job.run()
            return JsonResponse({"status": "DeliverContentsJob triggered"}, status=202)
        except Exception as e:
            metric_service.job_execution_failed(job_name=JobName.DELIVER_CONTENTS.value)
            return JsonResponse(
                {"status": "DeliverContentsJob failed", "error": str(e)}, status=500
            )


@method_decorator(check_api_key(), name="get")
class CheckIMAPJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            job = CheckIMAPJob()
            job.run()
            return JsonResponse({"status": "CheckIMAPJob triggered"}, status=202)
        except Exception as e:
            metric_service.job_execution_failed(job_name=JobName.CHECK_IMAP.value)
            return JsonResponse(
                {"status": "CheckIMAPJob failed", "error": str(e)}, status=500
            )


@method_decorator(check_api_key(), name="get")
class SendQuizRemindersJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            job = SendRemindersJob()
            job.run()
            return JsonResponse({"status": "SendRemidersJob triggered"}, status=202)
        except Exception as e:
            metric_service.job_execution_failed(job_name=JobName.SEND_REMINDERS.value)
            return JsonResponse(
                {"status": "SendRemidersJob failed", "error": str(e)}, status=500
            )


@method_decorator(check_api_key(), name="get")
class DeactivateInactiveEnrollmentsJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            job = DeactivateInactiveEnrollmentsJob()
            job.run()
            return JsonResponse(
                {"status": "DeactivateInactiveEnrollmentsJob triggered"}, status=202
            )
        except Exception as e:
            metric_service.job_execution_failed(
                job_name=JobName.DEACTIVATE_ENROLLMENTS.value
            )
            return JsonResponse(
                {
                    "status": "DeactivateInactiveEnrollmentsJob failed",
                    "error": str(e),
                },
                status=500,
            )


@method_decorator(check_api_key(), name="get")
class SendNewslettersJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            job = SendNewslettersJob()
            job.run()
            return JsonResponse({"status": "SendNewslettersJob triggered"}, status=202)
        except Exception as e:
            metric_service.job_execution_failed(job_name=JobName.SEND_NEWSLETTERS.value)
            return JsonResponse(
                {"status": "SendNewslettersJob failed", "error": str(e)}, status=500
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
            return JsonResponse(
                {
                    "status": "CleanupJobExecutions failed",
                    "error": str(e),
                },
                status=500,
            )
