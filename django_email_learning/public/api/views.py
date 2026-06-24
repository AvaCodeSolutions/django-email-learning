from django.views import View
from django.http import JsonResponse
from pydantic import ValidationError
from django_email_learning.models import Course, Newsletter, NewsletterSubscriber
from django_email_learning.public.api.serializers import (
    EnrollmentRequest,
    NewsletterSubscribeRequest,
)
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


class NewsletterSubscribeView(View):
    def get_max_subscribers(self) -> int:
        from django.conf import settings

        return (
            getattr(settings, "DJANGO_EMAIL_LEARNING", {})
            .get("NEWSLETTERS", {})
            .get("MAX_SUBSCRIBER_PER_NEWSLETTER", 500)
        )

    def post(self, request, organization_id: int, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            data = NewsletterSubscribeRequest.model_validate(payload)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        newsletters = {
            n.id: n
            for n in Newsletter.objects.filter(
                id__in=data.newsletter_ids,
                organization_id=organization_id,
            )
        }

        invalid = set(data.newsletter_ids) - set(newsletters)
        if invalid:
            return JsonResponse(
                {"error": "One or more newsletter IDs are invalid."}, status=400
            )

        max_subscribers = self.get_max_subscribers()
        for newsletter in newsletters.values():
            already_subscribed = NewsletterSubscriber.objects.filter(
                newsletter=newsletter, email=data.email
            ).exists()
            if (
                not already_subscribed
                and newsletter.subscribers.count() >= max_subscribers
            ):
                return JsonResponse(
                    {
                        "error": f'Newsletter "{newsletter.title}" has reached its maximum number of subscribers.'
                    },
                    status=400,
                )

        for newsletter_id in newsletters:
            NewsletterSubscriber.objects.get_or_create(
                newsletter_id=newsletter_id,
                email=data.email,
            )

        return JsonResponse({"status": "subscribed"}, status=200)
