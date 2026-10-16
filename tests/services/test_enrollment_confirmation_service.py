import pytest
from django.core import mail

from django_email_learning.models import (
    ContentDelivery,
    DeactivationReason,
    EnrollmentConfirmation,
    EnrollmentStatus,
    GateUnlockSource,
)
from django_email_learning.services.enrollment_confirmation_service import (
    ConfirmOutcome,
    confirm_gated_enrollment,
)


@pytest.fixture
def gated_enrollment(course, course_lesson_content, enrollment):
    course.enrollment_confirmation = EnrollmentConfirmation.GATE
    course.enrollment_gate_key = "payment"
    course.save()
    return enrollment


def test_confirming_activates_the_enrollment_and_welcomes_the_learner(gated_enrollment):
    result = confirm_gated_enrollment(gated_enrollment, GateUnlockSource.API)

    assert result.outcome == ConfirmOutcome.CONFIRMED
    gated_enrollment.refresh_from_db()
    assert gated_enrollment.status == EnrollmentStatus.ACTIVE
    assert gated_enrollment.activated_at is not None
    assert ContentDelivery.objects.filter(enrollment=gated_enrollment).exists()
    assert [email.subject for email in mail.outbox] == ["Enrollment Verified"]


def test_confirming_again_changes_nothing(gated_enrollment):
    confirm_gated_enrollment(gated_enrollment, GateUnlockSource.API)

    result = confirm_gated_enrollment(gated_enrollment, GateUnlockSource.API)

    assert result.outcome == ConfirmOutcome.ALREADY_CONFIRMED
    assert ContentDelivery.objects.filter(enrollment=gated_enrollment).count() == 1
    assert len(mail.outbox) == 1


def test_an_ended_enrollment_is_not_confirmed(gated_enrollment):
    gated_enrollment.status = EnrollmentStatus.DEACTIVATED
    gated_enrollment.deactivation_reason = DeactivationReason.CANCELED
    gated_enrollment.save()

    result = confirm_gated_enrollment(gated_enrollment, GateUnlockSource.ADMIN)

    assert result.outcome == ConfirmOutcome.NOT_CONFIRMABLE
    assert mail.outbox == []


def test_a_course_confirmed_by_link_has_no_enrollment_gate(enrollment):
    with pytest.raises(ValueError):
        confirm_gated_enrollment(enrollment, GateUnlockSource.API)
