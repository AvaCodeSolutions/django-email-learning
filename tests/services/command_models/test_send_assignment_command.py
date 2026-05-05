from django_email_learning.services.command_models.send_assignment_command import (
    SendAssignmentCommand,
)
from django.core import mail


def test_send_assignment_command(db, course_assignment_content):
    assignment_link = "https://example.com/assignment/token-123"
    command = SendAssignmentCommand(
        command_name="send_assignment",
        content_id=course_assignment_content.id,
        email="test@example.com",
        link=assignment_link,
    )

    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == course_assignment_content.assignment.title
    assert "test@example.com" in email.to
    assert assignment_link in email.body
    assert len(email.alternatives) == 1
