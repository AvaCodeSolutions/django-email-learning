import datetime

import pytest
from django.core import mail
from django.utils import timezone

from django_email_learning.models import (
    ContentDelivery,
    DeliverySchedule,
    DeliveryStatus,
)
from django_email_learning.services.command_models.send_assignment_reminder_command import (
    SendAssignmentReminderCommand,
)


@pytest.fixture
def assignment_content_delivery(db, active_enrollment, course_assignment_content):
    course_assignment_content.is_published = True
    course_assignment_content.save()

    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content_id=course_assignment_content.id,
        hash_value="testhash",
    )
    delivery.delivery_schedules.add(DeliverySchedule.objects.create(status=DeliveryStatus.DELIVERED, delivery=delivery))
    return delivery


def test_send_assignment_reminder_command(db, assignment_content_delivery):
    assignment_link = "https://example.com/assignment/token-123"
    test_time = timezone.now() - datetime.timedelta(days=1)
    assignment_content_delivery.remind_at = test_time
    delivery_schedule = DeliverySchedule.objects.create(
        delivery=assignment_content_delivery,
        link=assignment_link,
    )
    command = SendAssignmentReminderCommand(
        delivery_schedule=delivery_schedule,
    )

    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert (
        email.subject
        == f"Reminder: Assignment '{delivery_schedule.delivery.course_content.assignment.title}' is due soon"
    )
    assert assignment_content_delivery.enrollment.learner.email in email.to
    assert assignment_link in email.body
    assert len(email.alternatives) == 1
    delivery_schedule.delivery.refresh_from_db()
    assert delivery_schedule.delivery.reminder_state == ContentDelivery.ReminderStatus.SENT
    assert delivery_schedule.delivery.remind_at is not None
    assert delivery_schedule.delivery.remind_at > test_time
