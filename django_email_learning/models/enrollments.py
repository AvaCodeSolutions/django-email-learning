from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
import random
import logging
from django.core.mail import EmailMultiAlternatives
from .organizations import Organization
from .courses import Course
from .enums.enrollment_status import EnrollmentStatus
from .enums.deactivation_reason import DeactivationReason
from django_email_learning.services.email_sender_service import EmailSenderService
from django_email_learning.services import jwt_service
from django_email_learning.services.metrics_service import MetricsService
from django.utils.translation import gettext_lazy as _
from django.template.loader import render_to_string
from .enums.delivery_status import DeliveryStatus
from .course_contents import CourseContent
from datetime import timedelta, datetime


logger = logging.getLogger(__name__)

METRIC_SERVICE = MetricsService()


class BlockedEmail(models.Model):
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        return self.email

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.email = self.email.lower()
        self.full_clean()
        super().save(*args, **kwargs)


class Learner(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    photo = models.ImageField(upload_to="learner_photos/", null=True, blank=True)

    def save(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.email = self.email.lower()
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def enrollments_count(self) -> dict[str, int]:
        return {
            "total": self.enrollment_set.count(),
            "completed": self.enrollment_set.filter(
                status=EnrollmentStatus.COMPLETED
            ).count(),
        }

    class Meta:
        unique_together = [["organization", "email"]]

    def __str__(self) -> str:
        return self.email


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
    activated_at = models.DateTimeField(null=True, blank=True)
    final_state_at = models.DateTimeField(null=True, blank=True)
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
        if self.status == EnrollmentStatus.ACTIVE and self.activated_at is None:
            self.activated_at = timezone.now()
        if self.status in [EnrollmentStatus.COMPLETED, EnrollmentStatus.DEACTIVATED]:
            if self.final_state_at is None:
                self.final_state_at = timezone.now()

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

    def graduate(self) -> None:
        with transaction.atomic():
            if self.status != EnrollmentStatus.ACTIVE:
                raise ValidationError(
                    "Only active enrollments can be marked as completed."
                )
            self.status = EnrollmentStatus.COMPLETED
            self.final_state_at = timezone.now()
            METRIC_SERVICE.user_completed_course(
                course_slug=self.course.slug,
                organization_id=self.course.organization.id,
            )
            logger.info(
                f"Learner ID {self.learner.id} has completed the course {self.course.title}."
            )
            self.save()
            self.send_certificate_form()

    def send_certificate_form(self) -> None:
        if self.status != EnrollmentStatus.COMPLETED:
            raise ValidationError(
                "Certificate form can only be sent for completed enrollments."
            )
        token_payload = {
            "enrollment_id": self.id,
        }
        logging.info(
            f"Executing SendCertificateFormCommand for enrollment ID {self.id}"
        )
        token = jwt_service.generate_jwt(token_payload, exp=datetime.max)
        certificate_path = reverse(
            "django_email_learning:personalised:certificate_form"
        )
        link = f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{certificate_path}?token={token}"

        subject = _("Finalize your Certificate")

        context = {
            "course_title": self.course.title,
            "organization_name": self.course.organization.name,
            "link": link,
        }
        payload = render_to_string("emails/certificate_form.txt", context)

        email_service = EmailSenderService()
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=payload,
            from_email=email_service.from_email,
            to=[self.learner.email],
        )
        email_message.attach_alternative(
            render_to_string("emails/certificate_form.html", context), "text/html"
        )

        email_service.send(email_message)
        logging.info(f"Certificate form email sent for enrollment ID {self.id}")

    def fail(self) -> None:
        if self.status != EnrollmentStatus.ACTIVE:
            raise ValidationError("Only active enrollments can be marked as failed.")
        self.status = EnrollmentStatus.DEACTIVATED
        self.deactivation_reason = DeactivationReason.FAILED
        self.final_state_at = timezone.now()
        METRIC_SERVICE.user_enrollment_deactivated(
            course_slug=self.course.slug,
            organization_id=self.course.organization.id,
            reason=DeactivationReason.FAILED,
        )
        logger.info(
            f"Learner ID {self.learner.id} has failed the course {self.course.title}."
        )
        self.save()

    @transaction.atomic()
    def schedule_first_content_delivery(self) -> None:
        from .deliveries import DeliverySchedule

        first_content = (
            CourseContent.objects.filter(course=self.course, is_published=True)
            .order_by("priority")
            .first()
        )
        if first_content:
            delivery = self.content_deliveries.create(course_content=first_content)
            scheduled = DeliverySchedule.objects.create(
                time=timezone.now() + timedelta(seconds=first_content.waiting_period),
                delivery=delivery,
            )
            scheduled.generate_link()
        else:
            raise ValidationError("No published content available to schedule.")

    @property
    def progress_percentage(self) -> int:
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

        progress = int((delivered_content / total_content) * 100)
        return progress


class Certificate(models.Model):
    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name="certificate"
    )
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
