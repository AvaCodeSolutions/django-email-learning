import email
from email.policy import default
from unittest.mock import patch

from django_email_learning.models import EnrollmentStatus
from django_email_learning.services.command_models.exceptions.blocked_email_error import (
    BlockedEmailError,
)
from django_email_learning.services.command_models.exceptions.enrollment_already_exists_error import (
    EnrollmentAlreadyExistsError,
)
from django_email_learning.services.command_models.exceptions.invalid_course_slug_error import (
    InvalidCourseSlugError,
)
from django_email_learning.services.defaults.imap_interface import ImapInterface


def _build_email_message(subject: str, from_email: str = "sender@example.com"):
    return email.message_from_string(
        f"From: Sender <{from_email}>\nSubject: {subject}\n\nHello",
        policy=default,
    )


def test_enroll_executes_enroll_command_for_existing_course(db, course):
    interface = ImapInterface()

    with patch(
        "django_email_learning.services.defaults.imap_interface.EnrollCommand"
    ) as enroll_command_cls:
        interface._enroll(
            "student@example.com",
            course.slug,
            course.imap_connection,
        )

    enroll_command_cls.assert_called_once_with(
        email="student@example.com",
        course_slug=course.slug,
        organization_id=course.organization.id,
        case_insensitive_course_slug=True,
    )
    enroll_command_cls.return_value.execute.assert_called_once()


def test_enroll_skips_when_course_does_not_exist(db, imap_connection, caplog):
    interface = ImapInterface()

    with caplog.at_level("WARNING"):
        interface._enroll("student@example.com", "missing-course", imap_connection)

    assert "does not exist" in caplog.text


def test_enroll_handles_known_command_errors(db, course):
    interface = ImapInterface()

    for exception in [
        InvalidCourseSlugError("bad slug"),
        EnrollmentAlreadyExistsError("exists"),
        BlockedEmailError("blocked"),
    ]:
        with patch(
            "django_email_learning.services.defaults.imap_interface.EnrollCommand"
        ) as enroll_command_cls:
            enroll_command_cls.return_value.execute.side_effect = exception
            interface._enroll(
                "student@example.com",
                course.slug,
                course.imap_connection,
            )


def test_verify_executes_verify_command_for_matching_enrollment(db, enrollment):
    interface = ImapInterface()
    enrollment.status = EnrollmentStatus.UNVERIFIED
    enrollment.course.enabled = True
    enrollment.course.save()
    enrollment.save()

    with patch(
        "django_email_learning.services.defaults.imap_interface.VerifyEnrollmentCommand"
    ) as verify_command_cls:
        interface._verify(
            enrollment.learner.email,
            enrollment.activation_code,
            enrollment.course.imap_connection,
        )

    verify_command_cls.assert_called_once_with(
        enrollment_id=enrollment.id,
        verification_code=enrollment.activation_code,
    )
    verify_command_cls.return_value.execute.assert_called_once()


def test_verify_skips_when_unverified_enrollment_not_found(db, enrollment, caplog):
    interface = ImapInterface()
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    with caplog.at_level("WARNING"):
        interface._verify(
            enrollment.learner.email,
            enrollment.activation_code,
            enrollment.course.imap_connection,
        )

    assert "No unverified enrollment found" in caplog.text


def test_drop_executes_unsubscribe_command(db, course):
    interface = ImapInterface()

    with patch(
        "django_email_learning.services.defaults.imap_interface.UnsubscribeCommand"
    ) as unsubscribe_cls:
        interface._drop(
            "student@example.com",
            course.slug,
            course.imap_connection,
        )

    unsubscribe_cls.assert_called_once_with(
        email="student@example.com",
        course_slug=course.slug,
        organization_id=course.organization.id,
        case_insensitive_course_slug=True,
    )
    unsubscribe_cls.return_value.execute.assert_called_once()


def test_handle_email_message_dispatches_to_enroll_handler(db, course):
    interface = ImapInterface()
    email_message = _build_email_message(subject=f"enroll {course.slug}")

    with patch.object(interface, "_enroll") as enroll_spy:
        interface.handle_email_message(email_message, course.imap_connection)

    enroll_spy.assert_called_once_with(
        "sender@example.com", course.slug, course.imap_connection
    )


def test_handle_email_message_rejects_invalid_subject_format(db, course, caplog):
    interface = ImapInterface()
    email_message = _build_email_message(subject="enroll")

    with caplog.at_level("WARNING"):
        interface.handle_email_message(email_message, course.imap_connection)

    assert "Invalid email subject format" in caplog.text


def test_handle_email_message_rejects_unknown_command(db, course, caplog):
    interface = ImapInterface()
    email_message = _build_email_message(subject="unknown sample-course")

    with caplog.at_level("WARNING"):
        interface.handle_email_message(email_message, course.imap_connection)

    assert "Invalid command in email subject" in caplog.text
