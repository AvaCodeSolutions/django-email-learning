import json
import logging
import uuid
from typing import List

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from django_email_learning.models import Course, Newsletter, NewsletterSubscriber, Organization
from django_email_learning.public.api.rate_limiting import get_client_ip, is_rate_limited
from django_email_learning.public.api.serializers import (
    EmbeddableEnrollmentRequest,
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
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.utils import mask_email

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMITS = {
    "PER_IP_LIMIT": 20,
    "PER_IP_WINDOW_SECONDS": 300,
    "PER_EMAIL_LIMIT": 5,
    "PER_EMAIL_WINDOW_SECONDS": 3600,
    "PER_TOKEN_LIMIT": 60,
    "PER_TOKEN_WINDOW_SECONDS": 300,
}

TOO_MANY_REQUESTS_MESSAGE = "Too many requests. Please try again later."
NOT_FOUND_MESSAGE = "Not found"
INVALID_JSON_MESSAGE = "Invalid JSON payload"


def embeddable_enrollment_enabled() -> bool:
    return bool(getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("EMBEDDABLE_ENROLLMENT_ENABLED", False))


def get_rate_limit_settings() -> dict:
    configured = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("EMBEDDABLE_ENROLLMENT_RATE_LIMITS", {})
    return {**DEFAULT_RATE_LIMITS, **configured}


def _default_max_subscribers() -> int:
    return (
        getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("NEWSLETTERS", {}).get("MAX_SUBSCRIBER_PER_NEWSLETTER", 500)
    )


def _perform_enrollment(
    *, organization_id: int, email: str, course_slug: str, subscribe_to_newsletter: bool
) -> JsonResponse:
    try:
        course = Course.objects.get(slug=course_slug, organization_id=organization_id, is_public=True)
    except Course.DoesNotExist:
        return JsonResponse({"error": "Course not found"}, status=404)

    command = EnrollCommand(email=email, course_slug=course_slug, organization_id=organization_id)
    try:
        command.execute()
    except EnrollmentAlreadyExistsError as e:
        logger.info(f"Enrollment already exists: {e}")
        return JsonResponse({"status": "already_enrolled"}, status=200)
    except BlockedEmailError as e:
        error_reference = uuid.uuid4()
        logger.warning(f"Blocked email error: {e} (error_id: {error_reference})")
        return JsonResponse({"error": "Email is blocked", "error_id": str(error_reference)}, status=403)
    except LearnerCapExceededError as e:
        error_reference = uuid.uuid4()
        logger.warning(f"Learner cap exceeded: {e} (error_id: {error_reference})")
        return JsonResponse({"error": "Not enough slots available", "error_id": str(error_reference)}, status=403)
    except Exception as e:
        error_reference = uuid.uuid4()
        logger.error(f"Unexpected error: {e} (error_id: {error_reference})")
        return JsonResponse({"error": "An unexpected error occurred", "error_id": str(error_reference)}, status=500)

    if subscribe_to_newsletter and course.newsletter_id:
        # Created unconfirmed here (no confirmation email sent) - the
        # enrollment itself still needs verifying, and VerifyEnrollmentCommand
        # confirms this same row once that happens, since verifying the
        # enrollment already proves ownership of this email address.
        NewsletterSubscriber.objects.get_or_create(newsletter_id=course.newsletter_id, email=email)

    return JsonResponse({"status": "enrolled"}, status=200)


def _send_newsletter_confirmation_email(subscriber: NewsletterSubscriber) -> None:
    """Emails a confirmation link for a newly-created, unconfirmed
    NewsletterSubscriber. Subscribers stay unconfirmed - and are excluded
    from sendouts - until they click through.
    """
    site_base_url = str(settings.DJANGO_EMAIL_LEARNING["SITE_BASE_URL"]).rstrip("/")
    confirmation_path = reverse(
        "django_email_learning:public:newsletter_confirm_subscription",
        kwargs={"token": subscriber.confirm_token},
    )
    template_context = {
        "newsletter_title": subscriber.newsletter.title,
        "organization_name": subscriber.newsletter.organization.name,
        "confirmation_link": f"{site_base_url}{confirmation_path}",
    }

    email = EmailMultiAlternatives(
        subject=_("Confirm your newsletter subscription"),
        body=render_to_string("emails/newsletter_confirmation.txt", template_context),
        from_email=email_sender_service.from_email,
        to=[subscriber.email],
    )
    email.attach_alternative(
        render_to_string("emails/newsletter_confirmation.html", template_context),
        "text/html",
    )
    email_sender_service.send(email)


def _perform_newsletter_subscribe(
    *, organization_id: int, email: str, newsletter_ids: List[int], max_subscribers: int
) -> JsonResponse:
    newsletters = {
        n.id: n
        for n in Newsletter.objects.filter(id__in=newsletter_ids, organization_id=organization_id).select_related(
            "organization"
        )
    }

    invalid = set(newsletter_ids) - set(newsletters)
    if invalid:
        return JsonResponse({"error": "One or more newsletter IDs are invalid."}, status=400)

    for newsletter in newsletters.values():
        already_subscribed = NewsletterSubscriber.objects.filter(newsletter=newsletter, email=email).exists()
        if not already_subscribed and newsletter.subscribers.count() >= max_subscribers:
            return JsonResponse(
                {"error": f'Newsletter "{newsletter.title}" has reached its maximum number of subscribers.'},
                status=400,
            )

    for newsletter in newsletters.values():
        subscriber, created = NewsletterSubscriber.objects.get_or_create(newsletter=newsletter, email=email)
        if created:
            _send_newsletter_confirmation_email(subscriber)

    return JsonResponse({"status": "confirmation_pending"}, status=200)


class EnrollView(View):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        try:
            payload = EnrollmentRequest.model_validate(json.loads(request.body))
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        return _perform_enrollment(
            organization_id=payload.organization_id,
            email=payload.email,
            course_slug=payload.course_slug,
            subscribe_to_newsletter=payload.subscribe_to_newsletter,
        )


class NewsletterSubscribeView(View):
    def get_max_subscribers(self) -> int:
        return _default_max_subscribers()

    def post(self, request, organization_id: int, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            data = NewsletterSubscribeRequest.model_validate(payload)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        return _perform_newsletter_subscribe(
            organization_id=organization_id,
            email=data.email,
            newsletter_ids=data.newsletter_ids,
            max_subscribers=self.get_max_subscribers(),
        )


class PublicCorsMixin:
    """Adds a wide-open CORS policy on top of a view, for endpoints meant to be
    called cross-origin from third-party sites embedding a widget. These take
    no cookies/credentials, so an open origin policy carries no session-hijack
    risk on its own; callers still go through EMBEDDABLE_ENROLLMENT_ENABLED, a
    per-organization embed_token, and rate limiting below.
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


class EmbedTokenResolverMixin:
    """Resolves the Organization addressed by the embed_token URL segment
    before dispatching to the view, and 404s if embedding is disabled
    deployment-wide or the token doesn't match any organization. A bad token
    is intentionally indistinguishable from a disabled feature, so callers
    can't use this to enumerate valid tokens.
    """

    organization: Organization

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        if not embeddable_enrollment_enabled():
            return JsonResponse({"error": NOT_FOUND_MESSAGE}, status=404)
        try:
            self.organization = Organization.objects.get(embed_token=kwargs.get("token"))
        except Organization.DoesNotExist:
            return JsonResponse({"error": NOT_FOUND_MESSAGE}, status=404)
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]


@method_decorator(csrf_exempt, name="dispatch")
class EmbeddableEnrollView(EmbedTokenResolverMixin, PublicCorsMixin, View):
    """Cross-origin counterpart to EnrollView for embedding on third-party
    sites, addressed by a per-organization embed_token in the URL rather than
    a caller-supplied organization_id (which would let anyone target any
    organization). Disabled unless
    DJANGO_EMAIL_LEARNING["EMBEDDABLE_ENROLLMENT_ENABLED"] is set, since
    opening this up is a per-deployment decision, not a default.
    """

    def post(self, request, token: str, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        rate_limits = get_rate_limit_settings()
        client_ip = get_client_ip(request)

        if is_rate_limited(
            f"public_api:embed_enroll:ip:{client_ip}",
            limit=rate_limits["PER_IP_LIMIT"],
            window_seconds=rate_limits["PER_IP_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded enrollment rate limit exceeded for IP {client_ip}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        if is_rate_limited(
            f"public_api:embed_enroll:token:{token}",
            limit=rate_limits["PER_TOKEN_LIMIT"],
            window_seconds=rate_limits["PER_TOKEN_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded enrollment rate limit exceeded for organization {self.organization.id}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        try:
            payload = EmbeddableEnrollmentRequest.model_validate(json.loads(request.body))
        except json.JSONDecodeError:
            return JsonResponse({"error": INVALID_JSON_MESSAGE}, status=400)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        if is_rate_limited(
            f"public_api:embed_enroll:email:{payload.email.lower()}",
            limit=rate_limits["PER_EMAIL_LIMIT"],
            window_seconds=rate_limits["PER_EMAIL_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded enrollment rate limit exceeded for email {mask_email(payload.email)}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        return _perform_enrollment(
            organization_id=self.organization.id,
            email=payload.email,
            course_slug=payload.course_slug,
            subscribe_to_newsletter=payload.subscribe_to_newsletter,
        )


@method_decorator(csrf_exempt, name="dispatch")
class EmbeddableNewsletterSubscribeView(EmbedTokenResolverMixin, PublicCorsMixin, View):
    """Cross-origin counterpart to NewsletterSubscribeView, gated by the same
    embed_token/EMBEDDABLE_ENROLLMENT_ENABLED checks as EmbeddableEnrollView.
    """

    def get_max_subscribers(self) -> int:
        return _default_max_subscribers()

    def post(self, request, token: str, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        rate_limits = get_rate_limit_settings()
        client_ip = get_client_ip(request)

        if is_rate_limited(
            f"public_api:embed_newsletter_subscribe:ip:{client_ip}",
            limit=rate_limits["PER_IP_LIMIT"],
            window_seconds=rate_limits["PER_IP_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded newsletter subscribe rate limit exceeded for IP {client_ip}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        if is_rate_limited(
            f"public_api:embed_newsletter_subscribe:token:{token}",
            limit=rate_limits["PER_TOKEN_LIMIT"],
            window_seconds=rate_limits["PER_TOKEN_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded newsletter subscribe rate limit exceeded for organization {self.organization.id}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        try:
            data = NewsletterSubscribeRequest.model_validate(json.loads(request.body))
        except json.JSONDecodeError:
            return JsonResponse({"error": INVALID_JSON_MESSAGE}, status=400)
        except ValidationError as e:
            return JsonResponse({"error": str(e)}, status=400)

        if is_rate_limited(
            f"public_api:embed_newsletter_subscribe:email:{data.email.lower()}",
            limit=rate_limits["PER_EMAIL_LIMIT"],
            window_seconds=rate_limits["PER_EMAIL_WINDOW_SECONDS"],
        ):
            logger.warning(f"Embedded newsletter subscribe rate limit exceeded for email {mask_email(data.email)}")
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)

        return _perform_newsletter_subscribe(
            organization_id=self.organization.id,
            email=data.email,
            newsletter_ids=data.newsletter_ids,
            max_subscribers=self.get_max_subscribers(),
        )
