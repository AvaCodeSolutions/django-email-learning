import json
import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from django_email_learning.models import Course, Newsletter, NewsletterSubscriber
from django_email_learning.public.api.rate_limiting import get_client_ip, is_rate_limited
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
from django_email_learning.services.command_models.exceptions.learner_cap_exceeded_error import (
    LearnerCapExceededError,
)
from django_email_learning.services.utils import mask_email

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMITS = {
    "PER_IP_LIMIT": 20,
    "PER_IP_WINDOW_SECONDS": 300,
    "PER_EMAIL_LIMIT": 5,
    "PER_EMAIL_WINDOW_SECONDS": 3600,
}

TOO_MANY_REQUESTS_MESSAGE = "Too many requests. Please try again later."


def embeddable_enrollment_enabled() -> bool:
    return bool(getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("EMBEDDABLE_ENROLLMENT_ENABLED", False))


def get_rate_limit_settings() -> dict:
    configured = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("EMBEDDABLE_ENROLLMENT_RATE_LIMITS", {})
    return {**DEFAULT_RATE_LIMITS, **configured}


class EnrollView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        # Logic for enrolling a user via public API
        payload = json.loads(request.body)
        try:
            serlizer = EnrollmentRequest.model_validate(payload)
            try:
                course = Course.objects.get(
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
            except EnrollmentAlreadyExistsError as e:
                logger.info(f"Enrollment already exists: {e}")
                return JsonResponse({"status": "already_enrolled"}, status=200)
            except BlockedEmailError as e:
                logger.error(f"Blocked email error: {e}")
                return JsonResponse({"error": str(e)}, status=403)
            except LearnerCapExceededError as e:
                logger.info(f"Learner cap exceeded: {e}")
                return JsonResponse({"error": str(e)}, status=403)

            if serlizer.subscribe_to_newsletter and course.newsletter_id:
                NewsletterSubscriber.objects.get_or_create(
                    newsletter_id=course.newsletter_id,
                    email=serlizer.email,
                )

            return JsonResponse({"status": "enrolled"}, status=200)

        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)


class PublicCorsMixin:
    """Adds a wide-open CORS policy on top of a view, for endpoints meant to be
    called cross-origin from third-party sites embedding a widget. These take
    no cookies/credentials, so an open origin policy carries no session-hijack
    risk on its own; callers still go through EMBEDDABLE_ENROLLMENT_ENABLED and
    rate limiting below.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        if request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        response["Access-Control-Max-Age"] = "86400"
        return response


@method_decorator(csrf_exempt, name="dispatch")
class EmbeddableEnrollView(PublicCorsMixin, EnrollView):
    """Cross-origin counterpart to EnrollView for embedding on third-party
    sites. Disabled unless DJANGO_EMAIL_LEARNING["EMBEDDABLE_ENROLLMENT_ENABLED"]
    is set, since opening this up is a per-deployment decision, not a default.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        if not embeddable_enrollment_enabled():
            return JsonResponse({"error": "Not found"}, status=404)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        rate_limits = get_rate_limit_settings()
        client_ip = get_client_ip(request)
        if is_rate_limited(
            f"public_api:embed_enroll:ip:{client_ip}",
            limit=rate_limits["PER_IP_LIMIT"],
            window_seconds=rate_limits["PER_IP_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded enrollment rate limit exceeded for IP {client_ip}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        try:
            email = EnrollmentRequest.model_validate(json.loads(request.body)).email
        except (json.JSONDecodeError, ValidationError):
            email = None  # let the base view's own parsing report the real error

        if email and is_rate_limited(
            f"public_api:embed_enroll:email:{email.lower()}",
            limit=rate_limits["PER_EMAIL_LIMIT"],
            window_seconds=rate_limits["PER_EMAIL_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded enrollment rate limit exceeded for email {mask_email(email)}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        return super().post(request, *args, **kwargs)


class NewsletterSubscribeView(View):
    def get_max_subscribers(self) -> int:
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
            return JsonResponse({"error": "One or more newsletter IDs are invalid."}, status=400)

        max_subscribers = self.get_max_subscribers()
        for newsletter in newsletters.values():
            already_subscribed = NewsletterSubscriber.objects.filter(newsletter=newsletter, email=data.email).exists()
            if not already_subscribed and newsletter.subscribers.count() >= max_subscribers:
                return JsonResponse(
                    {"error": f'Newsletter "{newsletter.title}" has reached its maximum number of subscribers.'},
                    status=400,
                )

        for newsletter_id in newsletters:
            NewsletterSubscriber.objects.get_or_create(
                newsletter_id=newsletter_id,
                email=data.email,
            )

        return JsonResponse({"status": "subscribed"}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class EmbeddableNewsletterSubscribeView(PublicCorsMixin, NewsletterSubscribeView):
    """Cross-origin counterpart to NewsletterSubscribeView, gated by the same
    EMBEDDABLE_ENROLLMENT_ENABLED setting as EmbeddableEnrollView.
    """

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        if not embeddable_enrollment_enabled():
            return JsonResponse({"error": "Not found"}, status=404)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, organization_id: int, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        rate_limits = get_rate_limit_settings()
        client_ip = get_client_ip(request)
        if is_rate_limited(
            f"public_api:embed_newsletter_subscribe:ip:{client_ip}",
            limit=rate_limits["PER_IP_LIMIT"],
            window_seconds=rate_limits["PER_IP_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded newsletter subscribe rate limit exceeded for IP {client_ip}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        try:
            email = NewsletterSubscribeRequest.model_validate(json.loads(request.body)).email
        except (json.JSONDecodeError, ValidationError):
            email = None  # let the base view's own parsing report the real error

        if email and is_rate_limited(
            f"public_api:embed_newsletter_subscribe:email:{email.lower()}",
            limit=rate_limits["PER_EMAIL_LIMIT"],
            window_seconds=rate_limits["PER_EMAIL_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded newsletter subscribe rate limit exceeded for email {mask_email(email)}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        return super().post(request, organization_id, *args, **kwargs)
