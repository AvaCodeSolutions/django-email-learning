from typing import Optional
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.urls import reverse
from datetime import datetime, timedelta
from django_email_learning.services import jwt_service
from django_email_learning.services.utils import get_private_file_storage, mask_email
from .deliveries import ContentDelivery
from .organizations import OrganizationUser
from .course_contents import Assignment
from django_email_learning.services.utils import PRIVATE_FILE_STORAGE


class QuizSubmission(models.Model):
    delivery = models.ForeignKey(
        ContentDelivery, on_delete=models.CASCADE, related_name="quiz_submissions"
    )
    score = models.IntegerField()
    is_passed = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.delivery.course_content.type != "quiz":
            raise ValidationError("Sent item must be associated with a quiz content.")
        already_submitted = QuizSubmission.objects.filter(
            delivery=self.delivery
        ).count()
        if (
            self.delivery.course_content.quiz.limited_attempts  # type: ignore[union-attr]
            and already_submitted >= self.delivery.times_delivered
        ):
            raise ValidationError(
                "Quiz submission count exceeds the number of times the quiz was sent."
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.delivery.course_content.quiz.title} | {self.delivery.enrollment.learner.email} | Score: {self.score} | Passed: {self.is_passed}"  # type: ignore[union-attr]


class AssignmentSubmission(models.Model):
    class SubmissionStatus(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending Review"
        REQUESTING_CHANGES = "requesting_changes", "Requesting Changes"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    delivery = models.OneToOneField(
        ContentDelivery,
        on_delete=models.CASCADE,
        related_name="assignment_submission",
        unique=True,
    )
    text_submission = models.TextField(null=True, blank=True)
    file_submission = models.FileField(
        storage=get_private_file_storage,
        upload_to="assignment_submissions/",
        null=True,
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.PENDING_REVIEW,
        db_index=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer = models.ForeignKey(
        OrganizationUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_assignments",
    )

    @staticmethod
    def save_file(file_path: str, delivery: ContentDelivery) -> str:
        if PRIVATE_FILE_STORAGE.exists(file_path):
            if PRIVATE_FILE_STORAGE.size(file_path) > 10 * 1024 * 1024:
                raise ValueError(
                    "File size exceeds the maximum allowed limit of 10 MB."
                )
            file = PRIVATE_FILE_STORAGE.open(file_path)
            final_path = f"organizations/{delivery.enrollment.course.organization.id}/assignments/{delivery.id}/{file_path.split('/')[-1]}"
            PRIVATE_FILE_STORAGE.save(final_path, file)
            PRIVATE_FILE_STORAGE.delete(file_path)
            return final_path
        else:
            raise ValueError("File does not exist.")

    def private_file_url(self) -> Optional[str]:
        if self.file_submission:
            org_id = self.delivery.enrollment.course.organization.id
            payload = {
                "org_id": org_id,
                "file_path": self.file_submission.path,
            }
            token = jwt_service.generate_jwt(
                payload=payload, exp=datetime.now() + timedelta(hours=3)
            )
            url = (
                reverse("django_email_learning:platform:private_file_view")
                + f"?token={token}"
            )
            return url
        return None

    @property
    def assignment(self) -> Assignment:
        if self.delivery.course_content.assignment:
            return self.delivery.course_content.assignment  # type: ignore[assignment]
        raise ValueError("Associated content is not an assignment.")

    @transaction.atomic
    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if not self.delivery.course_content.assignment:
            raise ValidationError(
                "Sent item must be associated with an assignment content."
            )
        if not self.text_submission and not self.file_submission:
            raise ValidationError(
                "At least one of text submission or file submission must be provided."
            )
        self.full_clean()
        if not self.pk and self.status != self.SubmissionStatus.PENDING_REVIEW:
            raise ValidationError("New submissions must have status 'pending_review'.")
        if (
            self.assignment.is_blocking
            and self.status == self.SubmissionStatus.APPROVED
        ):
            current_state = (
                AssignmentSubmission.objects.get(pk=self.pk).status if self.pk else None
            )
            if current_state != self.SubmissionStatus.APPROVED:
                self.delivery.schedule_next_delivery()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.delivery.course_content.assignment.title} | {mask_email(self.delivery.enrollment.learner.email)} | Submitted at: {self.submitted_at}"  # type: ignore[union-attr]


class AssignmentFeedback(models.Model):
    submission = models.ForeignKey(
        AssignmentSubmission, on_delete=models.CASCADE, related_name="feedbacks"
    )
    comment = models.TextField()
    provided_at = models.DateTimeField(auto_now_add=True)
    provided_by = models.ForeignKey(
        OrganizationUser,
        on_delete=models.SET_NULL,
        related_name="provided_feedbacks",
        null=True,
    )

    def __str__(self) -> str:
        return f"Feedback for {self.submission}"
