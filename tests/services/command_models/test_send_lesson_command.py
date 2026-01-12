from django_email_learning.services.command_models.send_lesson_command import (
    SendLessonCommand,
)
from django.core import mail


def test_send_lesson_command(db, lesson):
    command = SendLessonCommand(
        command_name="send_lesson",
        lesson_id=lesson.id,
        email="test@example.com",
    )
    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == lesson.title
    assert "test@example.com" in email.to
    assert lesson.content in email.body
