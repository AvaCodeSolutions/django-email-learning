import base64
import ipaddress
import re
import random
import uuid
from enum import StrEnum
from typing import Any
from django.conf import settings
from django.db import models, transaction
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ImproperlyConfigured
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from django.forms import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


FIXED_SALT = b"\x00" * 16


def is_domain_or_ip(value: str) -> None:
    """
    Validate if the given value is a valid domain name or IP address.

    Raises:
        ValueError: If the value is not a valid domain or IP address.
    """
    try:
        ipaddress.ip_address(value)
    except ValueError:
        DOMAIN_REGEX = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$")
        if not bool(DOMAIN_REGEX.match(value.lower())):
            raise ValueError(f"{value} is not a valid domain or IP address")


class Organization(models.Model):
    name = models.CharField(max_length=200, unique=True)
    logo = models.ImageField(upload_to="organization_logos/", null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class OrganizationUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=50,
        choices=[
            ("admin", "Admin"),
            ("editor", "Editor"),
            ("viewer", "Viewer"),
        ],
        db_index=True,
    )

    def __str__(self) -> str:
        return f"{self.user.username} - {self.organization.name}"


class ImapConnection(models.Model):
    server = models.CharField(max_length=200, validators=[is_domain_or_ip])
    port = models.IntegerField(db_default=993)
    email = models.EmailField(max_length=200, unique=True)
    password = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.email}|{self.server}:{self.port}"

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.password:
            self.password = self._encrypt_password(self.password)
        if self.server:
            self.server = self.server.lower()
        self.full_clean()
        super().save(*args, **kwargs)

    def _fernet(self) -> Fernet:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=FIXED_SALT, iterations=100000
        )
        try:
            secret = settings.DJANGO_EMAIL_LEARNING["ENCRYPTION_SECRET_KEY"]
        except (AttributeError, KeyError):
            raise ImproperlyConfigured(
                "DJANGO_EMAIL_LEARNING['ENCRYPTION_SECRET_KEY'] must be set in settings.py"
            )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        return Fernet(key)

    def _encrypt_password(self, password: str) -> str:
        f = self._fernet()
        return f.encrypt(password.encode()).decode()

    def decrypt_password(self, encrypted_password: str) -> str:
        f = self._fernet()
        return f.decrypt(encrypted_password.encode()).decode()


class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=50,
        help_text="A short label for the course, used in URLs or email interactive actions. You can not edit it later.",
    )
    description = models.TextField(null=True, blank=True)
    enabled = models.BooleanField(default=False)
    imap_connection = models.ForeignKey(
        ImapConnection, on_delete=models.SET_NULL, null=True, blank=True
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.title

    class Meta:
        unique_together = [["slug", "organization"], ["title", "organization"]]

    def delete(
        self, using: Any | None = None, keep_parents: bool = False
    ) -> tuple[int, dict[str, int]]:
        if self.enabled:
            raise ValueError(
                "Course can not be deleted when enabled, please disable the course first!"
            )
        return super().delete(using, keep_parents)


class Lesson(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()

    def __str__(self) -> str:
        return self.title


class QuizSelectionStrategy(StrEnum):
    ALL_QUESTIONS = "all"
    RANDOM_QUESTIONS = "random"


class Quiz(models.Model):
    title = models.CharField(max_length=500)
    required_score = models.IntegerField(validators=[MaxValueValidator(100)])
    selection_strategy = models.CharField(
        max_length=50,
        choices=[
            (QuizSelectionStrategy.ALL_QUESTIONS.value, "All Questions"),
            (QuizSelectionStrategy.RANDOM_QUESTIONS.value, "Random Questions"),
        ],
    )
    deadline_days = models.IntegerField(
        help_text="Time limit to complete the quiz in days. Minimum is 1 day and maximum is 30 days.",
        validators=[MinValueValidator(1), MaxValueValidator(30)],
    )

    class Meta:
        verbose_name_plural = "Quizzes"

    def __str__(self) -> str:
        return self.title

    def validate_questions(self) -> None:
        if not self.questions.exists():
            raise ValidationError("At least one question is required.")

        for question in self.questions.all():
            try:
                question.validate_answers()
            except ValidationError as e:
                raise ValidationError(f"For question '{question.text}', {e.message}")


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=500)
    priority = models.IntegerField()

    def __str__(self) -> str:
        return self.text

    def validate_answers(self) -> None:
        if not self.answers.filter(is_correct=True).exists():
            raise ValueError("At least one correct answer is required.")

        if self.answers.count() < 2:
            raise ValueError("At least two answers are required.")

    def is_multiple_choice(self) -> bool:
        return self.answers.filter(is_correct=True).count() > 1


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.text

    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:  # type: ignore[no-untyped-def]
        if self.question.quiz.coursecontent_set.filter(is_published=True).exists():
            raise ValidationError("Cannot delete answers from a published quiz.")
        return super().delete(*args, **kwargs)


class CourseContent(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    priority = models.IntegerField()
    type = models.CharField(
        max_length=50,
        choices=[
            ("lesson", "Lesson"),
            ("quiz", "Quiz"),
        ],
    )
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, null=True, blank=True, on_delete=models.CASCADE)
    waiting_period = models.IntegerField(
        help_text="Waiting period in seconds after previous content is sent or submited."
    )
    is_published = models.BooleanField(default=False)

    def __str__(self) -> str:
        if self.type == "lesson" and self.lesson:
            return f"{self.priority} - Lesson: {self.lesson.title}"
        elif self.type == "quiz" and self.quiz:
            return f"{self.priority} - Quiz: {self.quiz.title}"
        return f"{self.course.title} content #{self.priority}"

    @property
    def title(self) -> str:
        if self.type == "lesson" and self.lesson:
            return self.lesson.title
        elif self.type == "quiz" and self.quiz:
            return self.quiz.title
        return "Untitled Content"

    def _validate_content(self) -> None:
        if self.type == "lesson" and not self.lesson:
            raise ValidationError("Lesson must be provided for lesson content.")
        if self.type == "quiz" and not self.quiz:
            raise ValidationError("Quiz must be provided for quiz content.")
        if self.type == "lesson" and self.lesson:
            self.lesson.full_clean()
        elif self.type == "quiz" and self.quiz:
            self.quiz.full_clean()

    def full_clean(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._validate_content()
        return super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "quiz"],
                condition=models.Q(quiz__isnull=False),
                name="unique_quiz_per_course",
            ),
            models.UniqueConstraint(
                fields=["course", "lesson"],
                condition=models.Q(lesson__isnull=False),
                name="unique_lesson_per_course",
            ),
            models.UniqueConstraint(
                fields=["course", "priority"],
                name="unique_priority_per_course",
            ),
        ]


class BlockedEmail(models.Model):
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return self.email

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.email = self.email.lower()
        self.full_clean()
        super().save(*args, **kwargs)


class Learner(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.email = self.email.lower()
        self.full_clean()
        super().save(*args, **kwargs)


class EnrollmentStatus(StrEnum):
    UNVERIFIED = "unverified"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEACTIVATED = "deactivated"


class DeactivationReason(StrEnum):
    CANCELED = "canceled"
    BLOCKED = "blocked"
    FAILED = "failed"
    INACTIVE = "inactive"


class Enrollment(models.Model):
    state_transitions = {
        EnrollmentStatus.UNVERIFIED: [
            EnrollmentStatus.ACTIVE,
            EnrollmentStatus.DEACTIVATED,
        ],
        EnrollmentStatus.ACTIVE: [
            EnrollmentStatus.COMPLETED,
            EnrollmentStatus.DEACTIVATED,
        ],
        EnrollmentStatus.COMPLETED: [],
        EnrollmentStatus.DEACTIVATED: [],
    }
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=50,
        choices=[
            (EnrollmentStatus.UNVERIFIED, "Unverified"),
            (EnrollmentStatus.ACTIVE, "Active"),
            (EnrollmentStatus.COMPLETED, "Completed"),
            (EnrollmentStatus.DEACTIVATED, "Deactivated"),
        ],
        default=EnrollmentStatus.UNVERIFIED,
    )
    deactivation_reason = models.CharField(
        null=True,
        blank=True,
        choices=[
            (DeactivationReason.CANCELED, "Canceled"),
            (DeactivationReason.BLOCKED, "Blocked"),
            (DeactivationReason.FAILED, "Failed"),
            (DeactivationReason.INACTIVE, "Inactive"),
        ],
        max_length=50,
    )
    activation_code = models.CharField(max_length=6, null=True, blank=True)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.pk:
            old_status = Enrollment.objects.get(pk=self.pk).status
            old_status = EnrollmentStatus(old_status)
            if old_status != self.status:
                allowed_transitions = self.state_transitions.get(old_status, [])
                if self.status not in allowed_transitions:
                    raise ValidationError(
                        f"Invalid status transition from {old_status} to {self.status}."
                    )
        else:
            self.activation_code = "".join(random.choices("0123456789", k=6))
        if self.status != "deactivated" and self.deactivation_reason is not None:
            raise ValidationError(
                "Deactivation reason must be null unless status is 'deactivated'."
            )
        if self.status == "deactivated" and not self.deactivation_reason:
            raise ValidationError(
                "Deactivation reason must be provided when status is 'deactivated'."
            )
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.learner.email} - {self.course.title} ({self.status})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "course"],
                condition=models.Q(status__in=["unverified", "active", "completed"]),
                name="unique_active_enrollment",
            )
        ]

    @transaction.atomic()
    def schedule_first_content_delivery(self) -> None:
        first_content = (
            CourseContent.objects.filter(course=self.course, is_published=True)
            .order_by("priority")
            .first()
        )
        if first_content:
            delivery = ContentDelivery.objects.create(
                enrollment=self,
                course_content=first_content,
            )
            DeliverySchedule.objects.create(
                time=timezone.now() + timedelta(seconds=first_content.waiting_period),
                delivery=delivery,
            )
        else:
            raise ValidationError("No published content available to schedule.")


class ContentDelivery(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    course_content = models.ForeignKey(CourseContent, on_delete=models.CASCADE)
    hash_value = models.CharField(max_length=64, null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["enrollment", "course_content"]]

    @property
    def times_delivered(self) -> int:
        return self.delivery_schedules.filter(is_delivered=True).count()

    def update_hash(self) -> None:
        self.hash_value = (
            base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")
        )
        self.save()

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        if not self.hash_value:
            self.hash_value = (
                base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("=")
            )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Delivery of {self.course_content.title} to {self.enrollment.learner.email}"


class DeliverySchedule(models.Model):
    delivery = models.ForeignKey(
        ContentDelivery, on_delete=models.CASCADE, related_name="delivery_schedules"
    )
    time = models.DateTimeField(default=timezone.now, db_index=True)
    is_delivered = models.BooleanField(default=False, db_index=True)

    def __str__(self) -> str:
        return f"Delivery for {self.delivery.course_content.title} to {self.delivery.enrollment.learner.email} at {self.time} - Delivered: {self.is_delivered}"


class QuizSubmission(models.Model):
    delivery = models.ForeignKey(ContentDelivery, on_delete=models.CASCADE)
    score = models.IntegerField()
    is_passed = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.delivery.course_content.type != "quiz":
            raise ValidationError("Sent item must be associated with a quiz content.")
        already_submitted = QuizSubmission.objects.filter(
            delivery=self.delivery
        ).count()
        if already_submitted >= self.delivery.times_delivered:
            raise ValidationError(
                "Quiz submission count exceeds the number of times the quiz was sent."
            )
        self.full_clean()
        super().save(*args, **kwargs)
