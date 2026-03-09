import uuid

from django.db import models


class SessionState(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"


class Session(models.Model):
    session_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    jwt_token = models.TextField()
    state = models.CharField(
        max_length=255,
        choices=SessionState.choices,
        default=SessionState.PENDING,
    )

    def save(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        super().save(*args, **kwargs)
