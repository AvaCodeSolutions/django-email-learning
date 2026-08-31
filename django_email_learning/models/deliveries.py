import base64
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from django_email_learning.services import jwt_service

from .course_contents import CourseContent, QuizSelectionStrategy
from .enrollments import Enrollment
from .enums.delivery_status import DeliveryStatus

logger = logging.getLogger(__name__)


class ContentDelivery(models.Model):
    # Cap on how many reminder emails a single delivery for deadline-less content
    # may receive before it stops nudging. Content with a deadline is always a
    # single reminder regardless of this value.
    MAX_RECURRING_REMINDERS = 3

    class ReminderStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "Not Applicable"
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        BLOCKED = "blocked", "Blocked"

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="content_deliveries")
    course_content = models.ForeignKey(CourseContent, on_delete=models.CASCADE)
    hash_value = models.CharField(max_length=64, null=True, blank=True)
    remind_at = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    reminder_state = models.CharField(
        max_length=50,
        choices=ReminderStatus.choices,
        default=ReminderStatus.NOT_APPLICABLE,
        db_index=True,
    )
    reminder_count = models.IntegerField(
        default=0,
        help_text="How many reminder emails have been sent for this delivery.",
    )
    opened_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        unique_together = [["enrollment", "course_content"]]

    @property
    def link(self) -> Optional[str]:
        latest_schedule = self.delivery_schedules.order_by("-time").first()
        if latest_schedule and latest_schedule.link:
            return latest_schedule.link
        return None

    @property
    def times_delivered(self) -> int:
        return self.delivery_schedules.filter(status=DeliveryStatus.DELIVERED).count()  # type: ignore[misc]

    def update_hash(self) -> None:
        self.hash_value = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")
        self.save()

    def schedule_next_delivery(self) -> Optional["ContentDelivery"]:
        """
        Schedules the next content delivery based on the current content's priority.
        Returns the ID of the newly created ContentDelivery if successful, otherwise None.
        """

        next_content = (
            CourseContent.objects.filter(
                course=self.course_content.course,
                is_published=True,
                priority__gt=self.course_content.priority,
            )
            .order_by("priority")
            .first()
        )
        if next_content:
            delivery, created = ContentDelivery.objects.get_or_create(
                enrollment=self.enrollment,
                course_content=next_content,
            )
            schedule = DeliverySchedule.objects.create(
                time=timezone.now() + timedelta(seconds=next_content.waiting_period),
                delivery=delivery,
            )
            schedule.generate_link()
            return delivery
        return None

    def repeat_delivery_in_days(self, days: int) -> bool:
        """
        Schedules a repeat delivery of the current content after a specified number of days.
        Returns True if the repeat delivery was scheduled, otherwise False.
        """
        schedule = DeliverySchedule.objects.create(
            time=timezone.now() + timedelta(days=days),
            delivery=self,
        )
        schedule.generate_link()
        logger.info(f"Repeat delivery scheduled for ContentDelivery ID {self.id} in {days} days.")
        return True

    def calculate_remind_at(self) -> Optional[datetime]:
        if self.course_content.quiz or self.course_content.assignment:
            if self.course_content.deadline_days and self.course_content.deadline_days > 0:
                if self.course_content.deadline_days > 1:
                    return timezone.now() + timedelta(days=self.course_content.deadline_days - 1)
                else:
                    return timezone.now() + timedelta(hours=(self.course_content.deadline_days * 24) - 10)
            else:
                if self.course_content.reminder_interval_days:
                    return timezone.now() + timedelta(days=self.course_content.reminder_interval_days)
        return None

    def record_reminder_sent(self) -> None:
        """
        Advance reminder bookkeeping after a reminder email has gone out.

        Content with a deadline gets a single reminder: it lands in SENT and
        stays there. Content without a deadline that has a reminder interval is
        re-armed for another nudge `reminder_interval_days` later, up to
        MAX_RECURRING_REMINDERS emails in total, after which it also settles in
        SENT. Submitting, graduating or failing resets `reminder_state` to
        NOT_APPLICABLE elsewhere, which stops the loop early.
        """
        self.reminder_count += 1
        interval = self.course_content.reminder_interval_days
        has_deadline = bool(self.course_content.deadline_days and self.course_content.deadline_days > 0)
        if not has_deadline and interval and self.reminder_count < self.MAX_RECURRING_REMINDERS:
            self.remind_at = timezone.now() + timedelta(days=interval)
            self.reminder_state = self.ReminderStatus.PENDING
        else:
            self.remind_at = timezone.now()
            self.reminder_state = self.ReminderStatus.SENT
        self.save()

    def calculate_valid_until(self) -> Optional[datetime]:
        if self.course_content.deadline_days and self.course_content.deadline_days > 0:
            return timezone.now() + timedelta(days=self.course_content.deadline_days)
        return None

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        if not self.hash_value:
            self.hash_value = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")
        if not self.pk:  # Only auto populate remind_at and valid_untill when the delivery is first created
            self.remind_at = self.calculate_remind_at()
            self.valid_until = self.calculate_valid_until()
            if self.remind_at:
                self.reminder_state = self.ReminderStatus.PENDING

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Delivery of {self.course_content.title} to {self.enrollment.learner.email}"


class DeliverySchedule(models.Model):
    delivery = models.ForeignKey(ContentDelivery, on_delete=models.CASCADE, related_name="delivery_schedules")
    time = models.DateTimeField(default=timezone.now, db_index=True)
    link = models.URLField(null=True, blank=True, max_length=500)
    status = models.CharField(
        max_length=50,
        choices=[
            (DeliveryStatus.SCHEDULED, "Scheduled"),
            (DeliveryStatus.PROCESSING, "Processing"),
            (DeliveryStatus.DELIVERED, "Delivered"),
            (DeliveryStatus.CANCELED, "Canceled"),
            (DeliveryStatus.BLOCKED, "Blocked"),
        ],
        default=DeliveryStatus.SCHEDULED,
        db_index=True,
    )
    failed_attempts = models.IntegerField(default=0)
    delivered_at = models.DateTimeField(null=True, blank=True, db_index=True)
    claimed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the schedule was moved to PROCESSING. Used to recover claims whose worker died.",
    )

    def generate_link(self) -> str:
        payload = {
            "delivery_id": self.delivery.id,
            "delivery_hash": self.delivery.hash_value,
        }
        if self.delivery.course_content.deadline_days:
            exp = self.time + timedelta(days=self.delivery.course_content.deadline_days)
        else:
            exp = datetime.max.replace(tzinfo=timezone.get_current_timezone())

        if self.delivery.course_content.quiz:
            if self.delivery.course_content.quiz.selection_strategy == QuizSelectionStrategy.RANDOM_QUESTIONS.value:
                payload["question_ids"] = self.delivery.course_content.quiz.random_question_ids()  # type: ignore[assignment]

            token = jwt_service.generate_jwt(payload=payload, exp=exp)
            quiz_path = reverse("django_email_learning:personalised:quiz_public_view")
            link = f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{quiz_path}?token={token}"
            self.link = link
            self.save()
            return link
        elif self.delivery.course_content.assignment:
            token = jwt_service.generate_jwt(payload=payload, exp=exp)
            assignment_path = reverse("django_email_learning:personalised:assignment_public_view")
            link = f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{assignment_path}?token={token}"
            self.link = link
            self.save()
            return link
        else:
            # TODO: Implement lesson link generation
            return ""

    def __str__(self) -> str:
        return (
            f"Delivery for {self.delivery.course_content.title} to {self.delivery.enrollment.learner.email} "
            f"at {self.time} - Status: {self.status}"
        )

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.status == DeliveryStatus.DELIVERED and not self.delivered_at:
            self.delivered_at = timezone.now()
        super().save(*args, **kwargs)
