import base64
import ipaddress
import re
from typing import Any
from django.conf import settings
from django.db import models
from django.core.validators import MaxValueValidator
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from django.forms import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone


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
        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
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
    is_published = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title


class Quiz(models.Model):
    title = models.CharField(max_length=500)
    required_score = models.IntegerField(validators=[MaxValueValidator(100)])
    is_published = models.BooleanField(default=False)

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

    def full_clean(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.is_published:
            try:
                self.validate_questions()
            except ValueError as e:
                if not self.pk:
                    raise ValidationError(
                        "Quiz can not be saved as published the first time. "
                        "please save unpublished and try to publish again."
                    )
                raise e

        super().full_clean(*args, **kwargs)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)


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
        if self.question.quiz.is_published:
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

    @property
    def is_published(self) -> bool:
        if self.type == "lesson" and self.lesson:
            return self.lesson.is_published
        elif self.type == "quiz" and self.quiz:
            return self.quiz.is_published
        return False

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


class Enrollment(models.Model):
    state_transitions = {
        "unverified": ["active", "deactivated"],
        "active": ["completed", "deactivated"],
        "completed": [],
        "deactivated": [],
    }
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    next_send_timestamp = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ("unverified", "Unverified"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("deactivated", "Deactivated"),
        ],
        default="unverified",
    )
    deactivation_reason = models.CharField(
        null=True,
        blank=True,
        choices=[
            ("canceled", "Canceled"),
            ("blocked", "Blocked"),
            ("failed", "Failed"),
            ("inactive", "Inactive"),
        ],
        max_length=50,
    )
    activation_code = models.CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.pk:
            old_status = Enrollment.objects.get(pk=self.pk).status
            if old_status != self.status:
                allowed_transitions = self.state_transitions.get(old_status, [])
                if self.status not in allowed_transitions:
                    raise ValidationError(
                        f"Invalid status transition from {old_status} to {self.status}."
                    )
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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "course"],
                condition=models.Q(status__in=["unverified", "active", "completed"]),
                name="unique_active_enrollment",
            )
        ]


class EventTimestamp(models.Model):
    time = models.DateTimeField(default=timezone.now, db_index=True)


class SentItem(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    course_content = models.ForeignKey(CourseContent, on_delete=models.CASCADE)
    send_events = models.ManyToManyField(EventTimestamp)
    times_sent = models.IntegerField(default=1)

    class Meta:
        unique_together = [["enrollment", "course_content"]]

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.full_clean()
        super().save(*args, **kwargs)
        if not self.send_events.exists():
            timestamp = EventTimestamp.objects.create()
            self.send_events.add(timestamp)


class QuizSubmission(models.Model):
    sent_item = models.ForeignKey(SentItem, on_delete=models.CASCADE)
    score = models.IntegerField()
    is_passed = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if self.sent_item.course_content.type != "quiz":
            raise ValidationError("Sent item must be associated with a quiz content.")
        self.full_clean()
        super().save(*args, **kwargs)
