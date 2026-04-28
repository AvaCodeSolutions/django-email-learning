from django.views import View
from django_email_learning.decorators import check_api_key
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.jobs.check_imap_job import CheckIMAPJob
from django_email_learning.jobs.send_reminders_job import SendRemindersJob
from django_email_learning.jobs.deactivate_inactive_enrollments_job import (
    DeactivateInactiveEnrollmentsJob,
)
from django.utils.decorators import method_decorator
from django.http import JsonResponse

from django_email_learning.models import JobName
from django_email_learning.services.metrics_service import MetricsService


metric_service = MetricsService()


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
