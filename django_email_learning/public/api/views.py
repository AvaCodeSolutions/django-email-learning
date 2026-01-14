from django.views import View
from django.http import JsonResponse
from pydantic import ValidationError
from django_email_learning.public.api.serializers import EnrollmentRequest
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.exceptions.invalid_course_slug_error import (
    InvalidCourseSlugError,
)
import json
import logging

logger = logging.getLogger(__name__)


class EnrollView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        # Logic for enrolling a user via public API
        payload = json.loads(request.body)
        try:
            serlizer = EnrollmentRequest.model_validate(payload)
            command = EnrollCommand(
                email=serlizer.email,
                course_slug=serlizer.course_slug,
                organization_id=serlizer.organization_id,
            )

            try:
                command.execute()
                return JsonResponse({"status": "enrolled"}, status=200)
            except InvalidCourseSlugError as e:
                logger.error(f"Invalid course slug error: {e}")
                return JsonResponse({"error": str(e)}, status=400)

        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
