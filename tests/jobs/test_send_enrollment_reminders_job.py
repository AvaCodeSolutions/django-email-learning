import re
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from django_email_learning.jobs.send_enrollment_reminders_job import SendEnrollmentRemindersJob
from django_email_learning.models import (
    DeactivationReason,
    Enrollment,
    EnrollmentConfirmation,
    EnrollmentStatus,
    JobExecution,
    JobStatus,
)
from django_email_learning.services.enrollment_emails import enrollment_email_open_url


@pytest.fixture
def enabled_course(course, course_lesson_content):
    course.enabled = True
    course.save()
    return course


@pytest.fixture
def gated_course(enabled_course):
    enabled_course.enrollment_confirmation = EnrollmentConfirmation.GATE
    enabled_course.enrollment_gate_key = "payment"
    enabled_course.enrollment_reminder_enabled = True
    enabled_course.save()
    return enabled_course


def enrolled(enrollment, hours_ago):
    Enrollment.objects.filter(id=enrollment.id).update(enrolled_at=timezone.now() - timedelta(hours=hours_ago))
    enrollment.refresh_from_db()
    return enrollment


def run():
    SendEnrollmentRemindersJob().run()


def test_an_unverified_enrollment_is_reminded_once_after_a_day(enabled_course, enrollment):
    enrolled(enrollment, 25)

    run()
    run()

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.subject == f"Reminder: verify your enrollment in {enabled_course.title}"
    assert "?token=" in sent.body
    enrollment.refresh_from_db()
    assert enrollment.enrollment_reminder_sent_at is not None
    assert enrollment.enrollment_reminder_type == "verification"
    assert JobExecution.objects.filter(status=JobStatus.COMPLETED).count() == 2


def test_nothing_is_sent_before_the_day_is_up(enabled_course, enrollment):
    enrolled(enrollment, 23)

    run()

    assert mail.outbox == []


def test_enrollments_older_than_the_window_are_left_alone(enabled_course, enrollment):
    enrolled(enrollment, 8 * 24)

    run()

    assert mail.outbox == []
    enrollment.refresh_from_db()
    assert enrollment.enrollment_reminder_sent_at is None


def test_verified_and_ended_enrollments_are_not_reminded(enabled_course, enrollment):
    enrollment.status = EnrollmentStatus.DEACTIVATED
    enrollment.deactivation_reason = DeactivationReason.CANCELED
    enrollment.save()
    enrolled(enrollment, 25)

    run()

    assert mail.outbox == []


def test_a_disabled_course_sends_no_reminders(course, enrollment):
    enrolled(enrollment, 25)

    run()

    assert mail.outbox == []


def test_a_gated_course_sends_no_reminder_unless_turned_on(gated_course, enrollment):
    gated_course.enrollment_reminder_enabled = False
    gated_course.save()
    enrolled(enrollment, 25)

    run()

    assert mail.outbox == []


def test_a_gated_course_sends_its_own_reminder(gated_course, enrollment):
    gated_course.enrollment_reminder_subject = "Still waiting on {{ course_title }}"
    gated_course.enrollment_reminder_body = (
        '<p>Pay now</p><a href="https://shop.example.com/pay" data-email-button="" '
        'data-query-params="ref=enrollment_id">Pay</a>'
    )
    gated_course.save()
    enrolled(enrollment, 25)

    run()

    [sent] = mail.outbox
    assert sent.subject == f"Still waiting on {gated_course.title}"
    assert f"https://shop.example.com/pay?ref={enrollment.id}" in sent.body
    assert "verify" not in sent.body.lower()
    enrollment.refresh_from_db()
    assert enrollment.enrollment_reminder_type == "enrollment"


def test_the_default_gated_reminder_is_sent_when_none_was_written(gated_course, enrollment):
    enrolled(enrollment, 25)

    run()

    assert mail.outbox[0].subject == f"Your enrollment in {gated_course.title} is still waiting"


def test_an_empty_gated_reminder_sends_nothing_and_records_nothing(gated_course, enrollment):
    gated_course.enrollment_reminder_body = "<p></p>"
    gated_course.save()
    enrolled(enrollment, 25)

    run()

    assert mail.outbox == []
    enrollment.refresh_from_db()
    assert enrollment.enrollment_reminder_sent_at is None


def test_a_failed_send_is_retried_on_the_next_run(enabled_course, enrollment):
    enrolled(enrollment, 25)

    with patch(
        "django_email_learning.jobs.send_enrollment_reminders_job.send_verification_reminder",
        side_effect=RuntimeError("SMTP down"),
    ):
        run()

    enrollment.refresh_from_db()
    assert enrollment.enrollment_reminder_sent_at is None

    run()

    assert len(mail.outbox) == 1


def test_the_window_comes_from_settings(settings, enabled_course, enrollment):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "ENROLLMENT_REMINDERS": {"AFTER_HOURS": 2, "MAX_AGE_DAYS": 1},
    }
    enrolled(enrollment, 3)

    run()

    assert len(mail.outbox) == 1


def test_the_window_can_be_overridden_per_run(enabled_course, enrollment):
    enrolled(enrollment, 3)

    SendEnrollmentRemindersJob(after_hours=2).run()

    assert len(mail.outbox) == 1


@pytest.mark.parametrize(("after_hours", "max_age_days"), [(0, 7), (48, 2)])
def test_a_window_that_can_never_match_is_refused(after_hours, max_age_days):
    with pytest.raises(ValueError):
        SendEnrollmentRemindersJob(after_hours=after_hours, max_age_days=max_age_days)


def test_opening_the_reminder_is_recorded_apart_from_the_first_email(enabled_course, enrollment):
    enrolled(enrollment, 25)
    run()

    html = mail.outbox[0].alternatives[0][0]
    [pixel] = re.findall(r'<img src="([^"]+/track/enrollment-reminder-open/[^"]+)"', html)
    Client().get(urlsplit(pixel).path)

    enrollment.refresh_from_db()
    assert enrollment.enrollment_reminder_opened_at is not None
    assert enrollment.enrollment_email_opened_at is None


def test_a_first_email_token_cannot_mark_the_reminder_opened(enrollment):
    token = urlsplit(enrollment_email_open_url(enrollment)).path.rstrip("/").rsplit("/", 1)[1]

    Client().get(reverse("django_email_learning:personalised:track_enrollment_reminder_open", kwargs={"token": token}))

    enrollment.refresh_from_db()
    assert enrollment.enrollment_reminder_opened_at is None


def test_the_timeline_shows_the_reminder_and_its_open(org_admin_client, enabled_course, enrollment):
    enrolled(enrollment, 25)
    run()
    Client().get(urlsplit(enrollment_email_open_url(enrollment, reminder=True)).path)

    url = reverse(
        "django_email_learning:api_platform:enrollments_detail",
        kwargs={"organization_id": 1, "enrollment_id": enrollment.id},
    )
    events = {event["type"]: event for event in org_admin_client.get(url).json()["events"]}

    assert events["enrollment_reminder_sent"]["event_data"] == {"email": "verification"}
    assert events["enrollment_reminder_opened"]["event_data"] == {"email": "verification"}
