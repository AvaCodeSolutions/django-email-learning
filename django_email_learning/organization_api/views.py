"""The organization-scoped public API (v1).

Authenticated with an organization API key rather than a session. Every view
reads the organization from `request.organization`, which the decorator takes
from the key itself — never from the request body or the URL, so a key can only
ever act on the organization it was issued for.

Distinct from `public.api`, which is the unauthenticated, embeddable surface
for third-party pages: that one is gated by a publishable embed token and is
deliberately limited to what an anonymous visitor may do.
"""

import json
import logging
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from django_email_learning.decorators import require_organization_api_key
from django_email_learning.models import (
    ApiKeyScope,
    Course,
    Enrollment,
    NewsletterSubscriber,
)
from django_email_learning.organization_api import serializers
from django_email_learning.public.api.rate_limiting import is_rate_limited
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.services.command_models.exceptions.invalid_course_slug_error import (
    InvalidCourseSlugError,
)
from django_email_learning.services.command_models.exceptions.learner_cap_exceeded_error import (
    LearnerCapExceededError,
)
from django_email_learning.services.utils import mask_email

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMITS = {
    "PER_KEY_LIMIT": 120,
    "PER_KEY_WINDOW_SECONDS": 60,
}

TOO_MANY_REQUESTS_MESSAGE = "Too many requests. Please try again later."
INVALID_JSON_MESSAGE = "Invalid JSON payload"


def get_rate_limit_settings() -> dict:
    configured = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("ORGANIZATION_API_RATE_LIMITS", {})
    return {**DEFAULT_RATE_LIMITS, **configured}


class RateLimitedApiView(View):
    """Applies a per-key request budget.

    Keyed on `key_id` rather than on the client IP: a server-to-server caller
    may sit behind a shared egress address, and the key is the thing whose
    usage we actually want to bound.
    """

    def check_rate_limit(self, request) -> JsonResponse | None:  # type: ignore[no-untyped-def]
        limits = get_rate_limit_settings()
        if is_rate_limited(
            f"org_api:{request.api_key.key_id}",
            limit=limits["PER_KEY_LIMIT"],
            window_seconds=limits["PER_KEY_WINDOW_SECONDS"],
        ):
            return JsonResponse({"error": TOO_MANY_REQUESTS_MESSAGE}, status=429)
        return None


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(require_organization_api_key(scopes=[ApiKeyScope.ENROLLMENTS_CREATE]), name="post")
class EnrollmentsView(RateLimitedApiView):
    def post(self, request, *args, **kwargs) -> JsonResponse:  # type: ignore[no-untyped-def]
        rate_limited = self.check_rate_limit(request)
        if rate_limited:
            return rate_limited

        try:
            payload = serializers.EnrollmentCreateRequest.model_validate(json.loads(request.body or "{}"))
        except json.JSONDecodeError:
            return JsonResponse({"error": INVALID_JSON_MESSAGE}, status=400)
        except ValidationError as e:
            return JsonResponse({"error": e.json()}, status=400)

        organization_id = request.organization.id

        # Unlike the embeddable endpoint this doesn't require the course to be
        # public - the caller holds a key for this organization, so a private
        # course of its own is legitimately within reach. It must still be
        # enabled, which EnrollCommand enforces.
        try:
            course = Course.objects.get(slug=payload.course_slug, organization_id=organization_id)
        except Course.DoesNotExist:
            return JsonResponse({"error": "Course not found"}, status=404)

        command = EnrollCommand(
            email=payload.email,
            course_slug=payload.course_slug,
            organization_id=organization_id,
        )
        try:
            command.execute()
        except EnrollmentAlreadyExistsError:
            return JsonResponse({"status": "already_enrolled"}, status=200)
        except InvalidCourseSlugError:
            return JsonResponse({"error": "Course not found"}, status=404)
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

        if payload.subscribe_to_newsletter and course.newsletter_id:
            # Created unconfirmed and without its own confirmation email: the
            # enrollment still has to be verified, and doing so proves ownership
            # of this address, which VerifyEnrollmentCommand then applies here.
            NewsletterSubscriber.objects.get_or_create(newsletter_id=course.newsletter_id, email=payload.email)

        enrollment = (
            Enrollment.objects.filter(
                learner__email=payload.email,
                learner__organization_id=organization_id,
                course=course,
            )
            .select_related("learner", "course")
            .order_by("-enrolled_at")
            .first()
        )
        logger.info(
            "API key %s enrolled %s in course '%s' (organization %s)",
            request.api_key.key_id,
            mask_email(payload.email),
            payload.course_slug,
            organization_id,
        )
        if enrollment is None:
            # Shouldn't happen - execute() succeeded - but returning a body
            # that claims an id we couldn't read would be worse than saying so.
            return JsonResponse({"status": "enrolled"}, status=201)
        return JsonResponse(
            {
                "status": "enrolled",
                "enrollment": serializers.EnrollmentResponse.from_django_model(enrollment).model_dump(mode="json"),
            },
            status=201,
        )
