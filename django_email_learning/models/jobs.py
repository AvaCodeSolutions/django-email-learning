from datetime import timedelta
from enum import StrEnum

from django.db import IntegrityError, models, transaction
from django.utils import timezone


class JobName(StrEnum):
    CHECK_IMAP = "check_imap"
    DELIVER_CONTENTS = "deliver_contents"
    SEND_REMINDERS = "send_reminders"
    DEACTIVATE_ENROLLMENTS = "deactivate_enrollments"
    SEND_NEWSLETTERS = "send_newsletters"


class JobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    STALE = "stale"
    FAILED = "failed"


class JobExecution(models.Model):
    job_name = models.CharField(max_length=200, choices=[(job.value, job.name) for job in JobName])
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=[(status.value, status.name) for status in JobStatus],
    )
    error = models.TextField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["job_name"],
                condition=models.Q(status=JobStatus.RUNNING.value),
                name="unique_running_jobexecution_per_job",
            )
        ]
        indexes = [
            models.Index(fields=["job_name", "-started_at"], name="jobexecution_name_started_idx"),
        ]

    @classmethod
    def start_if_not_running(cls, job_name: str, stale_after_hours: int = 2) -> "JobExecution | None":
        try:
            with transaction.atomic():
                stale_cutoff = timezone.now() - timedelta(hours=stale_after_hours)
                cls.objects.filter(
                    job_name=job_name,
                    status=JobStatus.RUNNING.value,
                    started_at__lt=stale_cutoff,
                ).update(status=JobStatus.STALE.value, finished_at=timezone.now())
                return cls.objects.create(
                    job_name=job_name,
                    status=JobStatus.RUNNING.value,
                    started_at=timezone.now(),
                )
        except IntegrityError:
            return None

    def __str__(self) -> str:
        return f"Job: {self.job_name} started at {self.started_at} - Status: {self.status}"
