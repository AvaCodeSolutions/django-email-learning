"""Reaching, unlocking and timing out gates.

A gate holds a learner until something outside the course unlocks it. The three ways
an enrollment's gate changes all live here so they agree on the rules:

* `reach_gate` - the delivery job arrives at a gate. A learner already holding an unlock
  walks through; anyone else is emailed the gate's message, if it has one, and waits.
* `unlock_gate` - the API or an admin unlocks it. A waiting learner moves on to what comes
  next; one who has not got there yet keeps the unlock for when they do.
* `expire_gate` - the gate's timeout passed with no unlock. Depending on the gate, the
  enrollment is deactivated or the learner continues as if it had been unlocked.

Reaching and unlocking both lock the enrollment row, so an unlock that lands while the
delivery job is reaching the same gate is never lost between the two.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Any, Optional

from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from django_email_learning.models import (
    ApiKey,
    ContentDelivery,
    CourseContent,
    CourseContentType,
    DeactivationReason,
    DeliverySchedule,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
    Gate,
    GateTimeoutAction,
    GateUnlock,
    GateUnlockSource,
)
from django_email_learning.services.command_models.send_gate_command import SendGateCommand
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service
from django_email_learning.services.utils import mask_email

logger = logging.getLogger(__name__)

# An unlock can be recorded before the learner has verified their address - a payment
# can clear first - but not once the enrollment has ended.
UNLOCKABLE_STATUSES = (EnrollmentStatus.UNVERIFIED, EnrollmentStatus.ACTIVE)


class UnlockOutcome(StrEnum):
    UNLOCKED = "unlocked"
    UNLOCKED_IN_ADVANCE = "unlocked_in_advance"
    ALREADY_UNLOCKED = "already_unlocked"
    NOT_UNLOCKABLE = "not_unlockable"


@dataclass(frozen=True)
class UnlockResult:
    outcome: UnlockOutcome
    enrollment_status: str


def reach_gate(delivery_schedule: DeliverySchedule) -> None:
    """Deliver a gate: let the learner through if it is unlocked, otherwise hold them.

    Raises whatever sending the gate's message raises, before anything is marked
    delivered, so the delivery job can retry it the way it retries any other email.
    """
    delivery = delivery_schedule.delivery
    content = delivery.course_content
    gate = content.gate
    if gate is None:
        raise ValueError(f"CourseContent {content.id} has no gate.")

    if gate.has_message and not _is_unlocked(delivery.enrollment_id, content.id):
        SendGateCommand(
            content_id=content.id, enrollment_id=delivery.enrollment_id, email=delivery.enrollment.learner.email
        ).execute()

    with transaction.atomic():
        enrollment = Enrollment.objects.select_for_update().get(id=delivery.enrollment_id)
        delivery_schedule.status = DeliveryStatus.DELIVERED
        delivery_schedule.save()

        if _is_unlocked(enrollment.id, content.id):
            logger.info(f"Enrollment {enrollment.id} reached gate {gate.key!r} already unlocked; moving on.")
            _move_past(delivery, enrollment)
            return

        if gate.timeout_days > 0:
            delivery.valid_until = timezone.now() + timedelta(days=gate.timeout_days)
            delivery.save()
        logger.info(f"Enrollment {enrollment.id} is waiting at gate {gate.key!r}.")
        _send_on_commit("gate_reached", enrollment=enrollment, course_content=content, gate=gate)


def unlock_gate(
    enrollment: Enrollment,
    course_content: CourseContent,
    source: GateUnlockSource,
    unlocked_by: Any = None,
    api_key: Optional[ApiKey] = None,
) -> UnlockResult:
    """Unlock `course_content`'s gate for `enrollment`. Safe to call more than once."""
    if course_content.type != CourseContentType.GATE or course_content.gate is None:
        raise ValueError(f"CourseContent {course_content.id} is not a gate.")
    if course_content.course_id != enrollment.course_id:
        raise ValueError(f"CourseContent {course_content.id} is not in enrollment {enrollment.id}'s course.")

    with transaction.atomic():
        locked = Enrollment.objects.select_for_update().get(id=enrollment.id)
        if locked.status not in UNLOCKABLE_STATUSES:
            return UnlockResult(UnlockOutcome.NOT_UNLOCKABLE, locked.status)

        unlock, created = GateUnlock.objects.get_or_create(
            enrollment=locked,
            course_content=course_content,
            defaults={"source": source, "unlocked_by": unlocked_by, "api_key": api_key},
        )
        if not created:
            return UnlockResult(UnlockOutcome.ALREADY_UNLOCKED, locked.status)

        reached = (
            ContentDelivery.objects.filter(
                enrollment=locked,
                course_content=course_content,
                delivery_schedules__status=DeliveryStatus.DELIVERED,
            )
            .distinct()
            .first()
        )
        if reached is not None and locked.status == EnrollmentStatus.ACTIVE:
            _move_past(reached, locked)
        outcome = UnlockOutcome.UNLOCKED if reached is not None else UnlockOutcome.UNLOCKED_IN_ADVANCE
        _send_on_commit(
            "gate_unlocked",
            enrollment=locked,
            course_content=course_content,
            gate=course_content.gate,
            unlock=unlock,
            was_waiting=reached is not None,
        )

    logger.info(f"Gate {course_content.gate.key!r} unlocked for enrollment {locked.id} by {source} ({outcome}).")
    locked.refresh_from_db()
    return UnlockResult(outcome, locked.status)


def expire_gate(delivery: ContentDelivery) -> None:
    """Apply the gate's timeout action to a learner whose wait has run out."""
    content = delivery.course_content
    gate = content.gate
    if gate is None:
        raise ValueError(f"CourseContent {content.id} has no gate.")

    if gate.timeout_action == GateTimeoutAction.CONTINUE:
        unlock_gate(delivery.enrollment, content, GateUnlockSource.TIMEOUT)
        return

    with transaction.atomic():
        enrollment = Enrollment.objects.select_for_update().get(id=delivery.enrollment_id)
        delivery.valid_until = None
        delivery.save()
        if enrollment.status != EnrollmentStatus.ACTIVE:
            return
        enrollment.status = EnrollmentStatus.DEACTIVATED
        enrollment.deactivation_reason = DeactivationReason.GATE_EXPIRED
        enrollment.save()

    logger.info(
        f"Deactivated enrollment {enrollment.id} for learner {mask_email(enrollment.learner.email)}: "
        f"gate {gate.key!r} was not unlocked within {gate.timeout_days} days."
    )
    _send_expired_email(enrollment, gate)
    metric_service.user_enrollment_deactivated(
        course_slug=content.course.slug,
        organization_id=content.course.organization_id,
        reason=DeactivationReason.GATE_EXPIRED.value,
    )


def _is_unlocked(enrollment_id: int, course_content_id: int) -> bool:
    return GateUnlock.objects.filter(enrollment_id=enrollment_id, course_content_id=course_content_id).exists()


def _move_past(delivery: ContentDelivery, enrollment: Enrollment) -> None:
    delivery.valid_until = None
    delivery.save()
    if not delivery.schedule_next_delivery():
        enrollment.graduate()


def _send_on_commit(signal_name: str, **kwargs: Any) -> None:
    # Imported here: the signals module pulls in django.contrib.auth models, which the
    # models package must not depend on at import time.
    from django_email_learning import signals

    signal = getattr(signals, signal_name)
    transaction.on_commit(lambda: signal.send(sender=Gate, **kwargs))


def _send_expired_email(enrollment: Enrollment, gate: Gate) -> None:
    course = enrollment.course
    context = {
        "gate_title": gate.title,
        "timeout_days": gate.timeout_days,
        "course_title": course.title,
        "organization_name": course.organization.name,
        **email_sender_service.organization_footer_context(course),
    }
    email_message = EmailMultiAlternatives(
        subject=_("Your enrollment in %(course_title)s has ended") % {"course_title": course.title},
        body=render_to_string("emails/gate_expired.txt", context),
        from_email=email_sender_service.from_email_for_course(course),
        to=[enrollment.learner.email],
    )
    email_message.attach_alternative(render_to_string("emails/gate_expired.html", context), "text/html")
    email_sender_service.send(email_message)
