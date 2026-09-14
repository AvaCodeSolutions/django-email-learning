"""Sending a decision point, reminding a learner who has not answered it, and a missed deadline."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from django_email_learning.jobs.deactivate_inactive_enrollments_job import DeactivateInactiveEnrollmentsJob
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.jobs.send_reminders_job import SendRemindersJob
from django_email_learning.models import (
    ContentDelivery,
    CourseContent,
    DecisionOption,
    DecisionPoint,
    DeliverySchedule,
    DeliveryStatus,
    EnrollmentStatus,
    Lesson,
)
from django_email_learning.services import jwt_service
from django_email_learning.services.command_models.send_decision_command import SendDecisionCommand
from django_email_learning.services.command_models.send_decision_reminder_command import (
    SendDecisionReminderCommand,
)
from django_email_learning.services.command_models.send_quiz_reminder_command import SendQuizReminderCommand
from tests.jobs.delivery_queue_mock import DeliveryQueueMock

LINK = "https://example.com/decision/?token=abc"


@pytest.fixture
def reminder_queue_mock():
    mock = DeliveryQueueMock()
    with patch(
        "django_email_learning.services.defaults.database_reminder_queue.DatabaseReminderQueue",
        return_value=mock,
    ):
        yield mock


@pytest.fixture
def decision_content(db, course):
    decision = DecisionPoint.objects.create(title="Pick your path", prompt="Basics first, or a deeper dive?")
    DecisionOption.objects.create(decision=decision, text="Basics", order=1)
    DecisionOption.objects.create(decision=decision, text="Deeper dive", order=2)
    content = CourseContent.objects.create(
        course=course, priority=1, type="decision", decision=decision, waiting_period=3600, is_published=True
    )
    CourseContent.objects.create(
        course=course,
        priority=2,
        type="lesson",
        lesson=Lesson.objects.create(title="Wrap up", content="..."),
        waiting_period=3600,
        is_published=True,
    )
    return content


@pytest.fixture
def decision_schedule(decision_content, active_enrollment):
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=decision_content)
    return DeliverySchedule.objects.create(delivery=delivery)


def test_sending_a_decision_waits_for_the_answer_before_scheduling_more(decision_schedule):
    with patch.object(SendDecisionCommand, "execute", return_value=None) as execute:
        DeliverContentsJob().process_delivery(decision_schedule)

    execute.assert_called_once()
    decision_schedule.refresh_from_db()
    assert decision_schedule.status == DeliveryStatus.DELIVERED
    assert "/decision/?token=" in decision_schedule.link
    assert ContentDelivery.objects.filter(enrollment=decision_schedule.delivery.enrollment).count() == 1


def test_a_decision_that_fails_to_send_is_not_marked_delivered(decision_schedule):
    with patch.object(SendDecisionCommand, "execute", side_effect=RuntimeError("SMTP unavailable")):
        DeliverContentsJob().process_delivery(decision_schedule)

    decision_schedule.refresh_from_db()
    assert decision_schedule.status != DeliveryStatus.DELIVERED


def test_the_decision_email_carries_the_question_and_the_link(decision_schedule, active_enrollment):
    SendDecisionCommand(
        content_id=decision_schedule.delivery.course_content.id,
        email=active_enrollment.learner.email,
        link=LINK,
    ).execute()

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.subject == "Pick your path"
    assert "Basics first, or a deeper dive?" in message.body
    assert LINK in message.body
    html = message.alternatives[0][0]
    assert f'href="{LINK}"' in html


def test_an_unanswered_decision_gets_the_decision_reminder(reminder_queue_mock, decision_schedule):
    delivery = decision_schedule.delivery
    delivery.reminder_state = ContentDelivery.ReminderStatus.PENDING
    delivery.save()
    reminder_queue_mock.add_task(decision_schedule)

    with (
        patch.object(
            SendDecisionReminderCommand,
            "execute",
            autospec=True,
            side_effect=lambda self: self.delivery_schedule.delivery.record_reminder_sent(),
        ) as decision_execute,
        patch.object(SendQuizReminderCommand, "execute", return_value=None) as quiz_execute,
    ):
        SendRemindersJob().run()

    decision_execute.assert_called_once()
    quiz_execute.assert_not_called()


def test_the_decision_reminder_links_back_to_the_question(decision_schedule):
    decision_schedule.link = LINK
    decision_schedule.save()

    SendDecisionReminderCommand(delivery_schedule=decision_schedule).execute()

    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Reminder: Pick your path"
    assert LINK in mail.outbox[0].body


def test_a_missed_decision_deadline_moves_the_learner_on_instead_of_deactivating(decision_schedule):
    delivery = decision_schedule.delivery
    delivery.valid_until = timezone.now() - timedelta(hours=1)
    delivery.save()

    DeactivateInactiveEnrollmentsJob().run()

    delivery.enrollment.refresh_from_db()
    assert delivery.enrollment.status == EnrollmentStatus.ACTIVE
    moved_on_to = ContentDelivery.objects.filter(enrollment=delivery.enrollment).exclude(id=delivery.id).get()
    assert moved_on_to.course_content.title == "Wrap up"


def send_decision_with_amp(decision_schedule, settings, amp_enabled):
    settings.DJANGO_EMAIL_LEARNING = {**settings.DJANGO_EMAIL_LEARNING, "AMP_ENABLED": amp_enabled}
    delivery = decision_schedule.delivery
    token = jwt_service.generate_jwt({"delivery_id": delivery.id, "delivery_hash": delivery.hash_value})
    SendDecisionCommand(
        content_id=delivery.course_content.id,
        email=delivery.enrollment.learner.email,
        link=f"https://example.com/decision/?token={token}",
    ).execute()
    return mail.outbox[0], token


def test_with_amp_enabled_the_decision_email_can_be_answered_inside_it(decision_schedule, settings):
    message, token = send_decision_with_amp(decision_schedule, settings, amp_enabled=True)

    assert [mimetype for _, mimetype in message.alternatives] == ["text/html", "text/x-amp-html"]
    amp = message.alternatives[1][0]
    assert reverse("django_email_learning:api_personalised:decision_amp_submission") in amp
    assert f'value="{token}"' in amp
    for option in decision_schedule.delivery.course_content.decision.options.all():
        assert f'name="option_id" value="{option.id}"' in amp
        assert option.text in amp


def test_without_amp_the_decision_email_has_no_amp_part(decision_schedule, settings):
    message, _ = send_decision_with_amp(decision_schedule, settings, amp_enabled=False)

    assert [mimetype for _, mimetype in message.alternatives] == ["text/html"]
