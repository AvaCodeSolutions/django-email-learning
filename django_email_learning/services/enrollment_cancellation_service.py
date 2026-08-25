"""Cancels a single enrollment on behalf of an organization admin.

A learner can end their own enrollment by unsubscribing, and the inactivity
job ends one that has gone stale, but until now an admin had no way to stop a
course they had started for someone - a learner who left the company, was
enrolled by mistake, or asked for it over another channel kept receiving
content until the course ran out.

Cancelling deactivates the enrollment with `DeactivationReason.REVOKED` and
cancels every delivery still waiting to go out. The reason is deliberately not
`CANCELED`: that one means the learner unsubscribed themselves, and the two
read very differently both in the enrollment timeline and in the
`user_enrollment_deactivated` metric, which is broken down by reason.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

from django.db import transaction
from django.utils import timezone

from django_email_learning.models import (
    DeactivationReason,
    DeliverySchedule,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
)
from django_email_learning.services.metrics_service import metric_service
from django_email_learning.services.utils import mask_email

logger = logging.getLogger(__name__)

CANCELLABLE_STATUSES = (EnrollmentStatus.UNVERIFIED, EnrollmentStatus.ACTIVE)


class CancellationOutcome(StrEnum):
    CANCELED = "canceled"
    NOT_CANCELLABLE = "not_cancellable"


@dataclass(frozen=True)
class CancellationResult:
    outcome: CancellationOutcome
    enrollment_status: str


def cancel_enrollment(enrollment: Enrollment) -> CancellationResult:
    """Deactivate `enrollment` as revoked and stop its pending deliveries.

    An enrollment that is already in a final state - completed, or deactivated
    for any reason - is left untouched and reported as `NOT_CANCELLABLE`; those
    are exactly the states the enrollment FSM allows no transition out of.
    """
    with transaction.atomic():
        # Locked and re-read so a concurrent graduation, unsubscribe, or job
        # deactivation cannot land between the status check and the write.
        locked = Enrollment.objects.select_for_update().get(id=enrollment.id)
        if locked.status not in CANCELLABLE_STATUSES:
            logger.info(
                f"Cancellation skipped for enrollment ID {locked.id}: "
                f"status is {locked.status}, which is already final."
            )
            return CancellationResult(
                outcome=CancellationOutcome.NOT_CANCELLABLE,
                enrollment_status=locked.status,
            )

        # Only schedules still waiting are stopped. A delivery being sent right
        # now (`PROCESSING`) belongs to the delivery job or to a manual send,
        # and taking it away mid-flight would leave the schedule in a status
        # neither of them expects - that email is going out either way.
        canceled_deliveries = DeliverySchedule.objects.filter(
            delivery__enrollment=locked,
            status=DeliveryStatus.SCHEDULED,
        ).update(status=DeliveryStatus.CANCELED)

        locked.status = EnrollmentStatus.DEACTIVATED
        locked.deactivation_reason = DeactivationReason.REVOKED
        locked.final_state_at = timezone.now()
        locked.save()

    metric_service.user_enrollment_deactivated(
        course_slug=locked.course.slug,
        organization_id=locked.course.organization_id,
        reason=DeactivationReason.REVOKED.value,
    )
    logger.info(
        f"Enrollment ID {locked.id} for learner {mask_email(locked.learner.email)} was canceled by an "
        f"organization admin. {canceled_deliveries} pending deliveries were canceled."
    )
    return CancellationResult(
        outcome=CancellationOutcome.CANCELED,
        enrollment_status=locked.status,
    )
