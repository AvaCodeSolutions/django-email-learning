from django.views import View
from django_email_learning.decorators import check_api_key
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django.utils.decorators import method_decorator
from django.http import JsonResponse


@method_decorator(check_api_key(), name="get")
class DeliverContentsJobView(View):
    def get(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        job = DeliverContentsJob()
        job.run()
        return JsonResponse({"status": "DeliverContentsJob triggered"}, status=202)
