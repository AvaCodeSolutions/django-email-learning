import pytest
from django.core import mail

from django_email_learning.models import Enrollment, EnrollmentConfirmation, EnrollmentStatus
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.command_models.exceptions.invalid_enrollment_error import (
    InvalidEnrollmentError,
)
from django_email_learning.services.command_models.verify_enrollment_command import VerifyEnrollmentCommand


@pytest.fixture
def gated_course(course, course_lesson_content):
    course.enabled = True
    course.enrollment_confirmation = EnrollmentConfirmation.GATE
    course.enrollment_gate_key = "payment"
    course.save()
    return course


def _enroll(course):
    EnrollCommand(email="new@example.com", course_slug=course.slug, organization_id=course.organization_id).execute()
    return Enrollment.objects.get(learner__email="new@example.com", course=course)


def test_enrolling_in_a_gated_course_sends_the_enrollment_email_instead_of_a_verification(gated_course):
    enrollment = _enroll(gated_course)

    assert enrollment.status == EnrollmentStatus.UNVERIFIED
    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.subject == f"Complete your enrollment in {gated_course.title}"
    assert enrollment.activation_code not in sent.body
    assert "verify" not in sent.body.lower()


def test_a_learner_cannot_verify_a_gated_enrollment_themselves(gated_course):
    enrollment = _enroll(gated_course)

    with pytest.raises(InvalidEnrollmentError):
        VerifyEnrollmentCommand(enrollment_id=enrollment.id, verification_code=enrollment.activation_code).execute()

    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.UNVERIFIED


def test_a_trusted_caller_can_activate_a_gated_enrollment_directly(gated_course):
    enrollment = _enroll(gated_course)

    VerifyEnrollmentCommand(
        enrollment_id=enrollment.id, verification_code=enrollment.activation_code, skip_enrollment_gate=True
    ).execute()

    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.ACTIVE
