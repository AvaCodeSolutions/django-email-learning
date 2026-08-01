import pytest

from django_email_learning.models import EnrollmentStatus
from django_email_learning.services.command_models.exceptions.invalid_course_slug_error import (
    InvalidCourseSlugError,
)
from django_email_learning.services.command_models.unsubscribe_command import (
    UnsubscribeCommand,
)


def test_unsubscribe_command(db, enrollment):
    command = UnsubscribeCommand(
        command_name="unsubscribe",
        email=enrollment.learner.email,
        course_slug=enrollment.course.slug,
        organization_id=enrollment.course.organization.id,
    )
    command.execute()

    # check enrollment deactivated
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.DEACTIVATED
    assert enrollment.deactivation_reason == "canceled"
    assert enrollment.final_state_at is not None


def test_unsubscribe_command_is_idempotent(db, enrollment):
    command = UnsubscribeCommand(
        command_name="unsubscribe",
        email=enrollment.learner.email,
        course_slug=enrollment.course.slug,
        organization_id=enrollment.course.organization.id,
    )
    command.execute()
    command.execute()

    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.DEACTIVATED
    assert enrollment.deactivation_reason == "canceled"


def test_unsubscribe_nonexistent_course(db, learner):
    command = UnsubscribeCommand(
        command_name="unsubscribe",
        email=learner.email,
        course_slug="nonexistent-course",
        organization_id=1,
    )
    with pytest.raises(InvalidCourseSlugError):
        command.execute()


def test_unsubscribe_nonexistent_learner(db, course, caplog):
    command = UnsubscribeCommand(
        command_name="unsubscribe",
        email="nonexistent@example.com",
        course_slug=course.slug,
        organization_id=course.organization.id,
    )
    command.execute()
    # No error should be raised, but logger should note no learner found
    caplog_text = caplog.text
    assert "No learner found with email" in caplog_text
