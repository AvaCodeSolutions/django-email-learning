import pytest
from django.core import mail

from django_email_learning.models import Enrollment, EnrollmentStatus, Learner
from django_email_learning.services.command_models.enroll_command import (
    EnrollCommand,
    InvalidCourseSlugError,
)
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.services.command_models.exceptions.learner_cap_exceeded_error import (
    LearnerCapExceededError,
)


def test_enroll_command(db, course):
    course.enabled = True
    course.save()
    command = EnrollCommand(
        command_name="enroll",
        email="test@example.com",
        course_slug=course.slug,
        organization_id=course.organization.id,
    )
    command.execute()

    # check learner and enrollment created
    learner = Learner.objects.get(email="test@example.com", organization_id=course.organization.id)
    enrollment = Enrollment.objects.get(learner=learner, course=course, status=EnrollmentStatus.UNVERIFIED)

    # check verification email sent
    assert len(mail.outbox) == 1
    sent_email = mail.outbox[0]
    assert sent_email.to == ["test@example.com"]
    assert sent_email.from_email  # check from_email is set
    assert "Verify your enrollment" in sent_email.subject
    assert enrollment.activation_code in sent_email.body


def test_enroll_command_skip_verification_email(db, course):
    course.enabled = True
    course.save()
    command = EnrollCommand(
        command_name="enroll",
        email="test@example.com",
        course_slug=course.slug,
        organization_id=course.organization.id,
        no_verification=True,  # Set the flag to skip verification email
    )
    command.execute()

    # check learner and enrollment created
    learner = Learner.objects.get(email="test@example.com", organization_id=course.organization.id)
    Enrollment.objects.get(learner=learner, course=course, status=EnrollmentStatus.UNVERIFIED)

    # check no verification email sent
    assert len(mail.outbox) == 0


def test_enroll_command_for_blocked_email(db, blocked_email, course):
    command = EnrollCommand(
        command_name="enroll",
        email=blocked_email.email,
        course_slug=course.slug,
        organization_id=course.organization.id,
    )
    with pytest.raises(BlockedEmailError):
        command.execute()

    # check no learner or enrollment created
    assert not Learner.objects.filter(email=blocked_email.email).exists()
    assert not Enrollment.objects.filter(course=course).exists()

    # check no email sent
    assert len(mail.outbox) == 0


def test_existing_enrollment_skipped(db, learner, course):
    course.enabled = True
    course.save()
    # Create an existing enrollment
    Enrollment.objects.create(learner=learner, course=course, status=EnrollmentStatus.UNVERIFIED)

    command = EnrollCommand(
        command_name="enroll",
        email=learner.email,
        course_slug=course.slug,
        organization_id=course.organization.id,
    )
    with pytest.raises(EnrollmentAlreadyExistsError):
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


def test_enroll_command_rejects_new_learner_when_cap_reached(db, settings, course):
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    Learner.objects.create(email="existing@example.com", organization_id=course.organization_id)

    command = EnrollCommand(
        command_name="enroll",
        email="new@example.com",
        course_slug=course.slug,
        organization_id=course.organization_id,
    )
    with pytest.raises(LearnerCapExceededError):
        command.execute()

    assert not Learner.objects.filter(email="new@example.com").exists()
    assert len(mail.outbox) == 0


def test_enroll_command_allows_existing_learner_when_cap_reached(db, settings, course):
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    learner = Learner.objects.create(email="existing@example.com", organization_id=course.organization_id)

    command = EnrollCommand(
        command_name="enroll",
        email=learner.email,
        course_slug=course.slug,
        organization_id=course.organization_id,
    )
    command.execute()

    assert Enrollment.objects.filter(learner=learner, course=course).exists()


def test_enroll_command_unlimited_by_default(db, course):
    course.enabled = True
    course.save()
    for i in range(5):
        Learner.objects.create(email=f"learner{i}@example.com", organization_id=course.organization_id)

    command = EnrollCommand(
        command_name="enroll",
        email="new@example.com",
        course_slug=course.slug,
        organization_id=course.organization_id,
    )
    command.execute()

    assert Learner.objects.filter(email="new@example.com", organization_id=course.organization_id).exists()
