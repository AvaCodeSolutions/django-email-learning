from django_email_learning.services.command_models.send_lesson_command import (
    SendLessonCommand,
)
from django.core import mail


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
