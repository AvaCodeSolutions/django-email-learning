from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)
from django_email_learning.models import (
    EnrollmentStatus,
    ContentDelivery,
    DeliverySchedule,
)
from django_email_learning.services.command_models.exceptions.invalid_enrollment_error import (
    InvalidEnrollmentError,
)
from django_email_learning.services.command_models.exceptions.invalid_verification_code_error import (
    InvalidVerificationCodeError,
)
from pydantic import ValidationError
from django.core import mail
from django.conf import settings
import pytest


def test_verify_enrollment_command_initialization():
    command = VerifyEnrollmentCommand(
        enrollment_id=123,
        verification_code="321456",
    )

    assert command.command_name == "verify_enrollment"
    assert command.enrollment_id == 123
    assert command.verification_code == "321456"


@pytest.mark.parametrize(
    "enrollment_id,verification_code",
    [
        (0, "123456"),  # Invalid enrollment_id (too low)
        (-1, "123456"),  # Invalid enrollment_id (negative)
        (1, "99999"),  # Invalid verification_code (too low)
        (1, "1000000"),  # Invalid verification_code (too high)
        (1, "abcdef"),  # Invalid verification_code (not an integer)
    ],
)
def test_verify_enrollment_command_invalid_fields(enrollment_id, verification_code):
    with pytest.raises(ValidationError):
        VerifyEnrollmentCommand(
            enrollment_id=enrollment_id,
            verification_code=verification_code,
        )


def test_verify_enrollment_command_execute(db, enrollment, course_lesson_content):
    command = VerifyEnrollmentCommand(
        enrollment_id=enrollment.id,
        verification_code=enrollment.activation_code,
    )

    assert enrollment.status == EnrollmentStatus.UNVERIFIED

    command.execute()

    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.ACTIVE
    assert enrollment.activation_code is None
    assert enrollment.activated_at is not None

    delivery = ContentDelivery.objects.get(
        enrollment=enrollment, course_content=course_lesson_content
    )
    assert DeliverySchedule.objects.filter(delivery=delivery).exists()

    # Check that a confirmation email was sent
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert sent_email.to == [enrollment.learner.email]
    assert "Enrollment Verified" in sent_email.subject


def test_verify_enrollment_command_includes_course_image_in_html_email(
    db, enrollment, course_lesson_content
):
    enrollment.course.image = "course_images/course-cover.jpg"
    enrollment.course.save(update_fields=["image"])

    command = VerifyEnrollmentCommand(
        enrollment_id=enrollment.id,
        verification_code=enrollment.activation_code,
    )

    command.execute()

    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert len(sent_email.alternatives) == 1

    html_body, mime_type = sent_email.alternatives[0]
    assert mime_type == "text/html"
    expected_image_url = (
        f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL'].rstrip('/')}"
        f"{enrollment.course.image.url}"
    )
    assert f'src="{expected_image_url}"' in html_body


def test_verify_enrollment_command_renders_html_without_course_image(
    db, enrollment, course_lesson_content
):
    enrollment.course.image = None
    enrollment.course.save(update_fields=["image"])

    command = VerifyEnrollmentCommand(
        enrollment_id=enrollment.id,
        verification_code=enrollment.activation_code,
    )

    command.execute()

    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert len(sent_email.alternatives) == 1

    html_body, mime_type = sent_email.alternatives[0]
    assert mime_type == "text/html"
    assert 'class="email-cover"' not in html_body


def test_verify_enrollment_command_invalid_enrollment(db):
    command = VerifyEnrollmentCommand(
        enrollment_id=9999,  # Non-existent enrollment ID
        verification_code="123456",
    )

    with pytest.raises(InvalidEnrollmentError):
        command.execute()


def test_verify_enrollment_command_invalid_verification_code(db, enrollment):
    command = VerifyEnrollmentCommand(
        enrollment_id=enrollment.id,
        verification_code="999999",  # Incorrect code
    )

    with pytest.raises(InvalidVerificationCodeError):
        command.execute()
