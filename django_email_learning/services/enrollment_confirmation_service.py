"""Turning an unverified enrollment into an active one.

However an enrollment is confirmed - the learner following their verification link,
a trusted caller enrolling them already verified, or, for a course whose enrollments are
gated, the unlock API or an admin - `activate_enrollment` does the same work, so the
learner's first content and welcome email never depend on which way it came.

`confirm_gated_enrollment` is the gate's side: it is the unlock of the course's enrollment
gate, safe to call again, and locks the enrollment so two unlocks racing for the same
learner activate it once.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Optional

from django.db import transaction
from django.utils import timezone

from django_email_learning.models import ApiKey, Enrollment, EnrollmentStatus, GateUnlockSource, NewsletterSubscriber
from django_email_learning.services.enrollment_emails import send_welcome_email
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)


class ConfirmOutcome(StrEnum):
    CONFIRMED = "confirmed"
    ALREADY_CONFIRMED = "already_confirmed"
    NOT_CONFIRMABLE = "not_confirmable"


@dataclass(frozen=True)
class ConfirmResult:
    outcome: ConfirmOutcome
    enrollment_status: str


def activate_enrollment(enrollment: Enrollment) -> None:
    """Activate an unverified `enrollment` and schedule its first content.

    Does not send the welcome email - see `send_welcome_email` - so callers inside a
    transaction can send it once the activation is committed.
    """
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.activation_code = None
    enrollment.save()
    logger.info(f"Enrollment Verified: Enrollment ID {enrollment.id} has been activated")

    enrollment.schedule_first_content_delivery()
    logger.info(f"Content Delivery Scheduled: First content delivery scheduled for Enrollment ID {enrollment.id}")
    metric_service.user_enrollment_activated(enrollment.course.slug, enrollment.course.organization.id)

    # Confirm a pre-existing linked-newsletter subscription (if any). We intentionally do
    # not auto-create one here: opt-in is decided at enrollment time via subscribe_to_newsletter.
    newsletter = enrollment.course.newsletter
    if newsletter:
        subscriber = NewsletterSubscriber.objects.filter(newsletter=newsletter, email=enrollment.learner.email).first()
        if subscriber and not subscriber.is_confirmed:
            subscriber.confirmed_at = timezone.now()
            subscriber.save(update_fields=["confirmed_at"])


def confirm_gated_enrollment(
    enrollment: Enrollment,
    source: GateUnlockSource,
    unlocked_by: Any = None,
    api_key: Optional[ApiKey] = None,
) -> ConfirmResult:
    """Unlock `enrollment`'s course's enrollment gate, activating it if it is waiting there."""
    if not enrollment.course.is_enrollment_gated:
        raise ValueError(f"Course {enrollment.course_id} does not gate its enrollments.")
    return confirm_enrollment(enrollment, source, unlocked_by=unlocked_by, api_key=api_key)


def confirm_enrollment(
    enrollment: Enrollment,
    source: GateUnlockSource,
    unlocked_by: Any = None,
    api_key: Optional[ApiKey] = None,
) -> ConfirmResult:
    """Activate an unverified `enrollment` on someone else's word rather than the learner's.

    For a gated course this is unlocking its enrollment gate. For a course confirmed by
    email link it is an admin verifying the enrollment in the learner's place, when the
    learner can't use their link. Either way, how and by whom is recorded for the timeline.
    """
    with transaction.atomic():
        locked = Enrollment.objects.select_for_update().select_related("course", "learner").get(id=enrollment.id)
        if locked.status in (EnrollmentStatus.ACTIVE, EnrollmentStatus.COMPLETED):
            return ConfirmResult(ConfirmOutcome.ALREADY_CONFIRMED, locked.status)
        if locked.status != EnrollmentStatus.UNVERIFIED:
            return ConfirmResult(ConfirmOutcome.NOT_CONFIRMABLE, locked.status)
        locked.confirmation_source = source.value
        locked.confirmed_by = unlocked_by
        locked.confirmation_api_key = api_key
        activate_enrollment(locked)

    actor = f"user {unlocked_by.pk}" if unlocked_by is not None else f"API key {api_key.key_id}" if api_key else source
    logger.info(f"Enrollment {locked.id} confirmed by {actor} ({source}).")
    send_welcome_email(locked)
    return ConfirmResult(ConfirmOutcome.CONFIRMED, locked.status)
