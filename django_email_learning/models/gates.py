"""Unlocks of gates, and which enrollments are waiting at one.

An enrollment is *waiting* when it is active and has reached a gate - the gate's delivery
went out - that it holds no unlock for. That is derived rather than stored as a status:
the enrollment stays ACTIVE throughout, so the enrollment state machine, the one-active-
enrollment constraint and everything else that reads ACTIVE keep working unchanged.

An unlock is recorded per enrollment and gate content, and may be recorded before the
learner gets there - a payment that clears on day one opens a gate at lesson five - in
which case the learner walks through it without stopping.
"""

from typing import Optional

from django.conf import settings
from django.db import models
from django.db.models import Exists, OuterRef

from .api_keys import ApiKey
from .course_contents import CourseContent
from .deliveries import ContentDelivery, DeliverySchedule
from .enrollments import Enrollment
from .enums.course_content_type import CourseContentType
from .enums.delivery_status import DeliveryStatus
from .enums.enrollment_status import EnrollmentStatus


class GateUnlockSource(models.TextChoices):
    API = "api", "API"
    ADMIN = "admin", "Admin"
    TIMEOUT = "timeout", "Timeout"


class GateUnlock(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="gate_unlocks")
    course_content = models.ForeignKey(CourseContent, on_delete=models.CASCADE, related_name="gate_unlocks")
    unlocked_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, choices=GateUnlockSource.choices)
    unlocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The admin who unlocked it, when source is admin.",
    )
    api_key = models.ForeignKey(
        ApiKey,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The key the unlock call was made with, when source is api.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["enrollment", "course_content"], name="unique_gate_unlock"),
        ]

    def __str__(self) -> str:
        return f"{self.course_content.title} unlocked for enrollment {self.enrollment_id} ({self.source})"


def waiting_gate_deliveries() -> models.QuerySet[ContentDelivery]:
    """Gate deliveries whose learner has arrived and is still held there."""
    return ContentDelivery.objects.filter(
        course_content__type=CourseContentType.GATE,
        enrollment__status=EnrollmentStatus.ACTIVE,
    ).filter(
        Exists(DeliverySchedule.objects.filter(delivery=OuterRef("pk"), status=DeliveryStatus.DELIVERED)),
        ~Exists(
            GateUnlock.objects.filter(enrollment=OuterRef("enrollment"), course_content=OuterRef("course_content"))
        ),
    )


def is_waiting_at_gate() -> Exists:
    """An expression over Enrollment rows: true while the enrollment is held at a gate."""
    return Exists(waiting_gate_deliveries().filter(enrollment=OuterRef("pk")))


def waiting_gate_delivery(enrollment: Enrollment) -> Optional[ContentDelivery]:
    """The gate delivery `enrollment` is held at, if it is waiting at one."""
    return (
        waiting_gate_deliveries()
        .filter(enrollment=enrollment)
        .select_related("course_content__gate")
        .order_by("-id")
        .first()
    )
