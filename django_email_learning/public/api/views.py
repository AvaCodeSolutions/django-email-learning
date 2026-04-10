from django.views import View
from django.http import JsonResponse
from pydantic import ValidationError
from django_email_learning.models import Course
from django_email_learning.public.api.serializers import EnrollmentRequest
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
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
            try:
                Course.objects.get(
                    slug=serlizer.course_slug,
                    organization_id=serlizer.organization_id,
                    is_public=True,
                )
            except Course.DoesNotExist:
                return JsonResponse({"error": "Course not found"}, status=404)

            command = EnrollCommand(
                email=serlizer.email,
                course_slug=serlizer.course_slug,
                organization_id=serlizer.organization_id,
            )

            try:
                command.execute()
                return JsonResponse({"status": "enrolled"}, status=200)
            except EnrollmentAlreadyExistsError as e:
                logger.info(f"Enrollment already exists: {e}")
                return JsonResponse({"status": "already_enrolled"}, status=200)
            except BlockedEmailError as e:
                logger.error(f"Blocked email error: {e}")
                return JsonResponse({"error": str(e)}, status=403)

        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)
