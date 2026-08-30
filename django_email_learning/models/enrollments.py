import logging
import random
from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_email_learning.services import jwt_service
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service
from django_email_learning.services.utils import get_private_file_storage, resolve_private_or_public_file_url

from .course_contents import CourseContent
from .courses import Course
from .enums.deactivation_reason import DeactivationReason
from .enums.delivery_status import DeliveryStatus
from .enums.enrollment_status import EnrollmentStatus
from .organizations import Organization

logger = logging.getLogger(__name__)


class BlockedEmail(models.Model):
    """
    Stores email addresses that are blocked from enrolling in any course.
    Emails are normalized to lowercase on save.
    """

    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return self.email

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.email = self.email.lower()
        self.full_clean()
        super().save(*args, **kwargs)


class Learner(models.Model):
    """
    Represents a student belonging to an Organization.
    Each learner is uniquely identified by their email within an organization.
    A learner can have multiple enrollments across different courses.
    """

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(storage=get_private_file_storage, upload_to="learner_photos/", null=True, blank=True)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.email = self.email.lower()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def enrollments_count(self) -> dict[str, int]:
        return {
            "total": self.enrollments.count(),
            "completed": self.enrollments.filter(status=EnrollmentStatus.COMPLETED).count(),
        }

    @property
    def private_photo_url(self) -> str | None:
        if not self.photo:
            return None
        return resolve_private_or_public_file_url(organization_id=self.organization_id, file_path=str(self.photo.name))

    class Meta:
        unique_together = [["organization", "email"]]

    def __str__(self) -> str:
        return self.email


class Enrollment(models.Model):
    """
    Tracks a learner's progress through a course.
    Follows a 4-state FSM: UNVERIFIED -> ACTIVE -> COMPLETED | DEACTIVATED.
    State transitions are enforced in clean() and save().
    Each enrollment belongs to one learner and one course.
    A learner cannot have more than one active enrollment per course.
    """

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self._last_saved_status = self.status

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
    learner = models.ForeignKey(Learner, related_name="enrollments", on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name="enrollments", on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    final_state_at = models.DateTimeField(null=True, blank=True, db_index=True)
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
            (DeactivationReason.REVOKED, "Revoked"),
        ],
        max_length=50,
    )
    activation_code = models.CharField(max_length=6, null=True, blank=True)

    def clean(self) -> None:
        if self.pk:
            old_status = EnrollmentStatus(self._last_saved_status)
            if old_status != self.status:
                allowed_transitions = self.state_transitions.get(old_status, [])
                if self.status not in allowed_transitions:
                    raise ValidationError(f"Invalid status transition from {old_status} to {self.status}.")
        if self.status != EnrollmentStatus.DEACTIVATED.value and self.deactivation_reason is not None:
            raise ValidationError("Deactivation reason must be null unless status is 'deactivated'.")
        if self.status == EnrollmentStatus.DEACTIVATED.value and not self.deactivation_reason:
            raise ValidationError("Deactivation reason must be provided when status is 'deactivated'.")

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        if not self.pk:
            self.activation_code = "".join(random.choices("0123456789", k=6))
        self.full_clean()
        if self.status == EnrollmentStatus.ACTIVE and self.activated_at is None:
            self.activated_at = timezone.now()
        if self.status in [EnrollmentStatus.COMPLETED, EnrollmentStatus.DEACTIVATED]:
            if self.final_state_at is None:
                self.final_state_at = timezone.now()
        self._last_saved_status = self.status
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.learner.email} - {self.course.title} ({self.status})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "course"],
                condition=models.Q(
                    status__in=[
                        EnrollmentStatus.UNVERIFIED.value,
                        EnrollmentStatus.ACTIVE.value,
                        EnrollmentStatus.COMPLETED.value,
                    ]
                ),
                name="unique_active_enrollment",
            )
        ]

    def graduate(self) -> None:
        with transaction.atomic():
            if self.status != EnrollmentStatus.ACTIVE:
                raise ValidationError("Only active enrollments can be marked as completed.")
            self.status = EnrollmentStatus.COMPLETED
            self.final_state_at = timezone.now()
            metric_service.user_completed_course(
                course_slug=self.course.slug,
                organization_id=self.course.organization.id,
            )
            logger.info(f"Learner ID {self.learner.id} has completed the course {self.course.title}.")
            self.save()
        if self.course.send_certificate:
            transaction.on_commit(self.send_certificate_form)

    def send_certificate_form(self) -> None:
        if self.status != EnrollmentStatus.COMPLETED:
            raise ValidationError("Certificate form can only be sent for completed enrollments.")
        token_payload = {
            "enrollment_id": self.id,
        }
        logger.info(f"Executing SendCertificateFormCommand for enrollment ID {self.id}")
        token = jwt_service.generate_jwt(
            token_payload,
            exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()),
        )
        certificate_path = reverse("django_email_learning:personalised:certificate_form")
        link = f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{certificate_path}?token={token}"

        subject = _("Finalize your Certificate")

        context = {
            "course_title": self.course.title,
            "organization_name": self.course.organization.name,
            "link": link,
        }
        payload = render_to_string("emails/certificate_form.txt", context)

        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_sender_service.from_email_for_course(self.course),
            to=[self.learner.email],
        )
        email_message.attach_alternative(render_to_string("emails/certificate_form.html", context), "text/html")

        email_sender_service.send(email_message)
        logger.info(f"Certificate form email sent for enrollment ID {self.id}")

    def fail(self) -> None:
        if self.status != EnrollmentStatus.ACTIVE:
            raise ValidationError("Only active enrollments can be marked as failed.")
        self.status = EnrollmentStatus.DEACTIVATED
        self.deactivation_reason = DeactivationReason.FAILED
        self.final_state_at = timezone.now()
        metric_service.user_enrollment_deactivated(
            course_slug=self.course.slug,
            organization_id=self.course.organization.id,
            reason=DeactivationReason.FAILED,
        )
        logger.info(f"Learner ID {self.learner.id} has failed the course {self.course.title}.")
        self.save()

    @transaction.atomic()
    def schedule_first_content_delivery(self) -> None:
        from .deliveries import DeliverySchedule

        first_content = CourseContent.objects.filter(course=self.course, is_published=True).order_by("priority").first()
        if first_content:
            delivery = self.content_deliveries.create(course_content=first_content)
            scheduled = DeliverySchedule.objects.create(
                time=timezone.now() + timedelta(seconds=first_content.waiting_period),
                delivery=delivery,
            )
            scheduled.generate_link()
        else:
            raise ValidationError("No published content available to schedule.")

    def progress_percentage(self, extra_delivered: int = 0) -> int:
        total_content = self.course.coursecontent_set.filter(is_published=True).count()
        if total_content == 0:
            return 0
        delivered_content = (
            self.content_deliveries.filter(
                delivery_schedules__status=DeliveryStatus.DELIVERED,
                course_content__is_published=True,
            )
            .distinct()
            .count()
        )

        progress = int(((delivered_content + extra_delivered) / total_content) * 100)
        return progress

    @classmethod
    def bulk_progress_percentages(cls, enrollments: "list[Enrollment]") -> dict[int, int]:
        """
        Same result as calling progress_percentage() on each enrollment, but in 2
        queries total instead of 2 queries per enrollment. progress_percentage()
        always hits the DB itself (it doesn't use prefetched querysets), so any
        caller iterating over more than a handful of enrollments should use this
        instead — see AverageProgressView and DownloadLearnerProgressView for the
        intended usage.
        """
        from .deliveries import ContentDelivery

        enrollments = list(enrollments)
        if not enrollments:
            return {}

        course_ids = {enrollment.course_id for enrollment in enrollments}
        total_content_by_course = dict(
            CourseContent.objects.filter(course_id__in=course_ids, is_published=True)
            .values("course_id")
            .annotate(total=models.Count("id"))
            .values_list("course_id", "total")
        )

        enrollment_ids = [enrollment.id for enrollment in enrollments]
        delivered_by_enrollment = dict(
            ContentDelivery.objects.filter(
                enrollment_id__in=enrollment_ids,
                delivery_schedules__status=DeliveryStatus.DELIVERED,
                course_content__is_published=True,
            )
            .values("enrollment_id")
            .annotate(count=models.Count("id", distinct=True))
            .values_list("enrollment_id", "count")
        )

        result = {}
        for enrollment in enrollments:
            total_content = total_content_by_course.get(enrollment.course_id, 0)
            if not total_content:
                result[enrollment.id] = 0
                continue
            delivered_content = delivered_by_enrollment.get(enrollment.id, 0)
            result[enrollment.id] = int((delivered_content / total_content) * 100)
        return result


class Certificate(models.Model):
    """
    Issued to a learner upon completing a course enrollment.
    Each enrollment can have at most one certificate (OneToOne).
    Certificate number is generated from course, enrollment, and a random suffix.
    """

    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="certificate")
    issued_at = models.DateTimeField(auto_now_add=True)
    name_on_certificate = models.CharField(max_length=200)
    random_suffix = models.IntegerField()

    @property
    def certificate_number(self) -> str:
        return f"{self.enrollment.course.id}-{self.enrollment.id}-{self.id}-{self.random_suffix}"

    def save(  # type: ignore[no-untyped-def]
        self, *, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if not self.random_suffix:
            self.random_suffix = random.randint(100000, 999999)
        return super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
