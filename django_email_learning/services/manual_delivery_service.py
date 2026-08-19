"""Runs a single scheduled content delivery immediately, outside the job.

The delivery job claims whatever is due and processes it, which means an
operator who wants one learner to receive their next content *now* has no
lever other than editing the schedule's time and waiting for the next job
run - and the job runs on a cron, so "now" is really "some time within the
next interval". This module does the same work the job does for exactly one
`DeliverySchedule`, so the email goes out, the schedule is marked delivered,
and the follow-up scheduling (next content, or graduation) happens in the
same request.

The row is claimed with the same `SCHEDULED -> PROCESSING` compare-and-set the
database queue uses, so a job run happening at the same moment cannot pick up
the same schedule and send the content twice.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum

from django.utils import timezone

from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.models import DeliverySchedule, DeliveryStatus
from django_email_learning.ports.task_queue_protocol import TaskQueueProtocol
from django_email_learning.services.metrics_service import metric_service

logger = logging.getLogger(__name__)


class ManualDeliveryOutcome(StrEnum):
    DELIVERED = "delivered"
    NOT_SCHEDULED = "not_scheduled"
    FAILED = "failed"


@dataclass(frozen=True)
class ManualDeliveryResult:
    outcome: ManualDeliveryOutcome
    delivery_status: str


class _EmptyDeliveryQueue(TaskQueueProtocol[DeliverySchedule]):
    """A queue that never yields work.

    `DeliverContentsJob` builds its queue on construction, and the database
    queue claims a batch of due schedules the moment it is built. Sending one
    delivery must not take rows away from a running job, so the job instance
    used here is given a queue with nothing in it: only `process_delivery` is
    called, and that takes its schedule as an argument.
    """

    def next_task(self) -> DeliverySchedule | None:
        return None


def send_delivery_schedule_now(delivery_schedule: DeliverySchedule) -> ManualDeliveryResult:
    """Deliver `delivery_schedule` as if the job had just picked it up.

    Returns the outcome together with the schedule's resulting status. A
    schedule that is not `SCHEDULED` when the claim runs is left untouched and
    reported as `NOT_SCHEDULED` - it is already delivered, canceled, blocked,
    or in the hands of a running job.
    """
    claimed = DeliverySchedule.objects.filter(id=delivery_schedule.id, status=DeliveryStatus.SCHEDULED).update(
        status=DeliveryStatus.PROCESSING,
        # The delivery is happening now, so the schedule should say so: it keeps
        # `delivered_at` consistent with `time`, and a retry after a failed
        # attempt is then measured from now rather than from a future date.
        time=timezone.now(),
        claimed_at=timezone.now(),
    )
    if not claimed:
        delivery_schedule.refresh_from_db()
        logger.info(
            f"Manual delivery skipped for DeliverySchedule ID {delivery_schedule.id}: "
            f"status is {delivery_schedule.status}, not {DeliveryStatus.SCHEDULED}."
        )
        return ManualDeliveryResult(
            outcome=ManualDeliveryOutcome.NOT_SCHEDULED,
            delivery_status=delivery_schedule.status,
        )

    # Everything from here on runs with the row already claimed, so every exit -
    # including an unexpected one - has to leave it in a status the queue can
    # see again. Loading the schedule is inside the try for that reason: an
    # error there would otherwise return the row to no one.
    job = DeliverContentsJob(delivery_queue=_EmptyDeliveryQueue())
    claimed_schedule: DeliverySchedule | None = None
    try:
        claimed_schedule = DeliverySchedule.objects.select_related(
            "delivery__enrollment__learner",
            "delivery__course_content__course__organization",
            "delivery__course_content__course__imap_connection",
            "delivery__course_content__lesson",
            "delivery__course_content__quiz",
            "delivery__course_content__assignment",
        ).get(id=delivery_schedule.id)

        job.process_delivery(claimed_schedule)
    except Exception as e:
        if claimed_schedule is None:
            # The claim succeeded but the schedule could not be loaded, so
            # nothing was sent. Release it rather than blocking a delivery that
            # was never attempted.
            DeliverySchedule.objects.filter(id=delivery_schedule.id, status=DeliveryStatus.PROCESSING).update(
                status=DeliveryStatus.SCHEDULED,
                claimed_at=None,
            )
            logger.exception(
                f"Manual delivery for DeliverySchedule ID {delivery_schedule.id} failed before the schedule "
                f"could be loaded: {e}. Returning it to {DeliveryStatus.SCHEDULED}."
            )
            return ManualDeliveryResult(
                outcome=ManualDeliveryOutcome.FAILED,
                delivery_status=DeliveryStatus.SCHEDULED,
            )
        job.block_delivery(claimed_schedule, e)
        return ManualDeliveryResult(outcome=ManualDeliveryOutcome.FAILED, delivery_status=DeliveryStatus.BLOCKED)

    claimed_schedule.refresh_from_db()
    if claimed_schedule.status == DeliveryStatus.PROCESSING:
        # `process_delivery` recognised no content to send - a content row whose
        # type has no matching lesson/quiz/assignment. Leaving it PROCESSING
        # would hide it from the job forever, so hand it back to the schedule.
        logger.error(
            f"Manual delivery for DeliverySchedule ID {claimed_schedule.id} produced no delivery. "
            f"Returning it to {DeliveryStatus.SCHEDULED}."
        )
        claimed_schedule.status = DeliveryStatus.SCHEDULED
        claimed_schedule.claimed_at = None
        claimed_schedule.save()
        metric_service.delivery_schedule_blocked(claimed_schedule.delivery.course_content.id)
        return ManualDeliveryResult(outcome=ManualDeliveryOutcome.FAILED, delivery_status=claimed_schedule.status)

    if claimed_schedule.status != DeliveryStatus.DELIVERED:
        logger.warning(
            f"Manual delivery for DeliverySchedule ID {claimed_schedule.id} ended as {claimed_schedule.status}."
        )
        return ManualDeliveryResult(outcome=ManualDeliveryOutcome.FAILED, delivery_status=claimed_schedule.status)

    logger.info(f"Manual delivery completed for DeliverySchedule ID {claimed_schedule.id}.")
    return ManualDeliveryResult(outcome=ManualDeliveryOutcome.DELIVERED, delivery_status=claimed_schedule.status)
