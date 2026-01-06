from django_email_learning.services.command_models.enroll_command import (
    EnrollCommand,
    InvalidCourseSlugError,
)
from django_email_learning.models import Enrollment, Learner, EnrollmentStatus
from django.core import mail
import pytest


def test_enroll_command(db, course):
    command = EnrollCommand(
        command_name="enroll",
        email="test@example.com",
        course_slug=course.slug,
        organization_id=course.organization.id,
    )
    command.execute()

    # check learner and enrollment created
    learner = Learner.objects.get(email="test@example.com")
    enrollment = Enrollment.objects.get(
        learner=learner, course=course, status=EnrollmentStatus.UNVERIFIED
    )

    # check verification email sent
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert sent_email.to == ["test@example.com"]
    assert "Verify your enrollment" in sent_email.subject
    assert enrollment.activation_code in sent_email.body


def test_enroll_command_for_blocked_email(db, blocked_email, course):
    command = EnrollCommand(
        command_name="enroll",
        email=blocked_email.email,
        course_slug=course.slug,
        organization_id=course.organization.id,
    )
    command.execute()

    # check no learner or enrollment created
    assert not Learner.objects.filter(email=blocked_email.email).exists()
    assert not Enrollment.objects.filter(course=course).exists()

    # check no email sent
    assert len(mail.outbox) == 0


def test_existing_enrollment_skipped(db, learner, course):
    # Create an existing enrollment
    Enrollment.objects.create(
        learner=learner, course=course, status=EnrollmentStatus.UNVERIFIED
    )

    command = EnrollCommand(
        command_name="enroll",
        email=learner.email,
        course_slug=course.slug,
        organization_id=course.organization.id,
    )
    command.execute()

    # Check that no new enrollment is created
    enrollments = Enrollment.objects.filter(learner=learner, course=course)
    assert enrollments.count() == 1  # Still only one enrollment

    # Check that no email is sent
    assert len(mail.outbox) == 0


def test_enroll_command_nonexistent_course(db, learner):
    command = EnrollCommand(
        command_name="enroll",
        email=learner.email,
        course_slug="nonexistent-course",
        organization_id=1,
    )

    with pytest.raises(InvalidCourseSlugError):
        command.execute()

    # Check that no enrollment is created
    assert not Enrollment.objects.filter(learner=learner).exists()

    # Check that no email is sent
    assert len(mail.outbox) == 0
