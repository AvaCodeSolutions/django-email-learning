from django_email_learning.services.command_models.send_quiz_command import (
    SendQuizCommand,
)
from django.core import mail


def test_send_quiz_command(db, course_quiz_content):
    quiz_link = "https://example.com/quiz/token-123"
    command = SendQuizCommand(
        command_name="send_quiz",
        content_id=course_quiz_content.id,
        email="test@example.com",
        link=quiz_link,
    )

    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == course_quiz_content.quiz.title
    assert "test@example.com" in email.to
    assert quiz_link in email.body
    assert len(email.alternatives) == 1
    assert email.alternatives[0][1] == "text/html"


def test_send_quiz_command_with_amp_enabled(db, course_quiz_content, settings):
    settings.DJANGO_EMAIL_LEARNING["AMP_ENABLED"] = True
    quiz_link = "https://example.com/quiz/token-123"
    command = SendQuizCommand(
        command_name="send_quiz",
        content_id=course_quiz_content.id,
        email="test@example.com",
        link=quiz_link,
    )

    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == course_quiz_content.quiz.title
    assert "test@example.com" in email.to
    assert quiz_link in email.body
    assert len(email.alternatives) == 2
    assert email.alternatives[0][1] == "text/html"
    assert email.alternatives[1][1] == "text/x-amp-html"
