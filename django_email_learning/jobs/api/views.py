from django.views import View
from django_email_learning.decorators import check_api_key
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.jobs.check_imap_job import CheckIMAPJob
from django_email_learning.jobs.send_reminders_job import SendRemindersJob
from django.utils.decorators import method_decorator
from django.http import JsonResponse


@method_decorator(check_api_key(), name="get")
class DeliverContentsJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        job = DeliverContentsJob()
        job.run()
        return JsonResponse({"status": "DeliverContentsJob triggered"}, status=202)


@method_decorator(check_api_key(), name="get")
class CheckIMAPJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        job = CheckIMAPJob()
        job.run()
        return JsonResponse({"status": "CheckIMAPJob triggered"}, status=202)


@method_decorator(check_api_key(), name="get")
class SendQuizRemindersJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        job = SendRemindersJob()
        job.run()
        return JsonResponse({"status": "SendRemidersJob triggered"}, status=202)
