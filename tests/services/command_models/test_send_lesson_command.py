from django.core import mail

from django_email_learning.models import FromEmailType
from django_email_learning.services.command_models.send_lesson_command import (
    SendLessonCommand,
)
from django_email_learning.services.email_sender_service import email_sender_service


def test_send_lesson_command(db, course_lesson_content):
    command = SendLessonCommand(
        command_name="send_lesson",
        content_id=course_lesson_content.id,
        email="test@example.com",
    )
    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == course_lesson_content.lesson.title
    assert "test@example.com" in email.to
    assert course_lesson_content.lesson.content in email.body
    assert email.from_email == email_sender_service.from_email


def test_send_lesson_command_uses_organization_from_email(db, course_lesson_content, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "DOMAIN_WIDE_EMAIL": {"ENABLED": True, "DOMAIN": "learn.example.com"},
    }
    course = course_lesson_content.course
    course.from_email_type = FromEmailType.ORGANIZATION
    course.save()

    SendLessonCommand(
        command_name="send_lesson",
        content_id=course_lesson_content.id,
        email="test@example.com",
    ).execute()

    assert mail.outbox[0].from_email == email_sender_service.from_email_for_course(course)
    assert "@learn.example.com" in mail.outbox[0].from_email
