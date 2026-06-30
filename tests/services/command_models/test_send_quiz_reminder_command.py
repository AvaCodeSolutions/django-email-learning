import datetime

from django.core import mail
from django.utils import timezone

from django_email_learning.models import ContentDelivery, DeliverySchedule
from django_email_learning.services.command_models.send_quiz_reminder_command import (
    SendQuizReminderCommand,
)


def test_send_quiz_command(db, content_delivery):
    quiz_link = "https://example.com/quiz/token-123"
    test_time = timezone.now() - datetime.timedelta(days=1)
    content_delivery.remind_at = test_time
    delivery_schedule = DeliverySchedule.objects.create(
        delivery=content_delivery,
        link=quiz_link,
    )
    command = SendQuizReminderCommand(
        delivery_schedule=delivery_schedule,
    )

    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == f"Reminder: Quiz '{delivery_schedule.delivery.course_content.quiz.title}' is due soon"
    assert content_delivery.enrollment.learner.email in email.to
    assert quiz_link in email.body
    assert len(email.alternatives) == 1
    delivery_schedule.delivery.refresh_from_db()
    assert delivery_schedule.delivery.reminder_state == ContentDelivery.ReminderStatus.SENT
    assert delivery_schedule.delivery.remind_at is not None
    assert delivery_schedule.delivery.remind_at > test_time
