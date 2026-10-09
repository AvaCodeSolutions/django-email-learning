"""Reaching a gate, unlocking it, and timing out at it."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from django_email_learning.jobs.deactivate_inactive_enrollments_job import DeactivateInactiveEnrollmentsJob
from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.models import (
    ContentDelivery,
    DeactivationReason,
    DeliverySchedule,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
    GateTimeoutAction,
    GateUnlock,
    GateUnlockSource,
    Learner,
    is_waiting_at_gate,
    waiting_gate_delivery,
)
from django_email_learning.services import gate_service
from django_email_learning.services.command_models.send_gate_command import SendGateCommand
from django_email_learning.services.gate_service import UnlockOutcome, unlock_gate
from django_email_learning.signals import gate_reached, gate_unlocked


@pytest.fixture
def gate_schedule(gate_course, active_enrollment):
    """The learner's delivery of the Payment gate, due now."""
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=gate_course.gate_content)
    return DeliverySchedule.objects.create(delivery=delivery)


@pytest.fixture
def received():
    """Records the gate signals sent during a test."""
    calls: dict[str, list[dict]] = {"reached": [], "unlocked": []}

    def on_reached(sender, **kwargs):
        calls["reached"].append(kwargs)

    def on_unlocked(sender, **kwargs):
        calls["unlocked"].append(kwargs)

    gate_reached.connect(on_reached)
    gate_unlocked.connect(on_unlocked)
    yield calls
    gate_reached.disconnect(on_reached)
    gate_unlocked.disconnect(on_unlocked)


def next_contents(enrollment):
    return list(
        ContentDelivery.objects.filter(enrollment=enrollment)
        .exclude(course_content__type="gate")
        .values_list("course_content__lesson__title", flat=True)
    )


# ── reaching a gate ──────────────────────────────────────────────────────────


def test_reaching_a_locked_gate_holds_the_learner(
    gate_schedule, active_enrollment, received, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        DeliverContentsJob().process_delivery(gate_schedule)

    gate_schedule.refresh_from_db()
    assert gate_schedule.status == DeliveryStatus.DELIVERED
    assert next_contents(active_enrollment) == []
    assert waiting_gate_delivery(active_enrollment) == gate_schedule.delivery
    assert [call["enrollment"] for call in received["reached"]] == [active_enrollment]
    assert received["unlocked"] == []


def test_reaching_a_gate_emails_its_message(gate_schedule, active_enrollment):
    mail.outbox.clear()
    DeliverContentsJob().process_delivery(gate_schedule)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [active_enrollment.learner.email]
    assert mail.outbox[0].subject == "Payment"
    assert "https://example.com/pay" in mail.outbox[0].alternatives[0][0]


@pytest.mark.parametrize("message", ["", "<p></p>", "<p>&nbsp;</p>"])
def test_a_gate_without_a_message_sends_nothing(gate_course, gate_schedule, message):
    gate_course.gate.message = message
    gate_course.gate.save()
    mail.outbox.clear()

    DeliverContentsJob().process_delivery(gate_schedule)

    assert mail.outbox == []
    gate_schedule.refresh_from_db()
    assert gate_schedule.status == DeliveryStatus.DELIVERED


def test_a_gate_unlocked_in_advance_is_walked_through(
    gate_course, gate_schedule, active_enrollment, received, django_capture_on_commit_callbacks
):
    GateUnlock.objects.create(
        enrollment=active_enrollment, course_content=gate_course.gate_content, source=GateUnlockSource.API
    )
    mail.outbox.clear()

    with django_capture_on_commit_callbacks(execute=True):
        DeliverContentsJob().process_delivery(gate_schedule)

    assert next_contents(active_enrollment) == ["Paid lesson"]
    assert waiting_gate_delivery(active_enrollment) is None
    assert received["reached"] == []
    assert mail.outbox == []


def test_a_gate_timeout_counts_from_when_the_learner_reaches_it(gate_course, gate_schedule):
    gate_course.gate.timeout_days = 5
    gate_course.gate.save()
    delivery = gate_schedule.delivery
    # Created ahead of the waiting period, so it must not have started the clock.
    assert delivery.valid_until is None

    DeliverContentsJob().process_delivery(gate_schedule)

    delivery.refresh_from_db()
    assert delivery.valid_until == pytest.approx(timezone.now() + timedelta(days=5), abs=timedelta(minutes=1))


def test_a_failing_gate_email_is_retried_without_holding_the_learner(gate_schedule, active_enrollment):
    with patch.object(SendGateCommand, "execute", side_effect=RuntimeError("SMTP down")):
        DeliverContentsJob().process_delivery(gate_schedule)

    gate_schedule.refresh_from_db()
    assert gate_schedule.status == DeliveryStatus.SCHEDULED
    assert gate_schedule.failed_attempts == 1
    assert waiting_gate_delivery(active_enrollment) is None


# ── unlocking ────────────────────────────────────────────────────────────────


def test_unlocking_a_waiting_learner_moves_them_on(
    gate_course, waiting_enrollment, received, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        result = unlock_gate(waiting_enrollment, gate_course.gate_content, GateUnlockSource.API)

    assert result.outcome == UnlockOutcome.UNLOCKED
    assert next_contents(waiting_enrollment) == ["Paid lesson"]
    assert waiting_gate_delivery(waiting_enrollment) is None
    [call] = received["unlocked"]
    assert call["was_waiting"] is True
    assert call["unlock"].source == GateUnlockSource.API


def test_unlocking_before_the_learner_arrives_is_kept_for_later(
    gate_course, active_enrollment, received, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        result = unlock_gate(active_enrollment, gate_course.gate_content, GateUnlockSource.API)

    assert result.outcome == UnlockOutcome.UNLOCKED_IN_ADVANCE
    assert GateUnlock.objects.filter(enrollment=active_enrollment).exists()
    assert ContentDelivery.objects.filter(enrollment=active_enrollment).count() == 0
    assert received["unlocked"][0]["was_waiting"] is False


def test_an_unverified_enrollment_can_be_unlocked_in_advance(gate_course, enrollment):
    result = unlock_gate(enrollment, gate_course.gate_content, GateUnlockSource.API)

    assert result.outcome == UnlockOutcome.UNLOCKED_IN_ADVANCE


def test_unlocking_twice_changes_nothing(gate_course, waiting_enrollment):
    unlock_gate(waiting_enrollment, gate_course.gate_content, GateUnlockSource.API)

    result = unlock_gate(waiting_enrollment, gate_course.gate_content, GateUnlockSource.ADMIN)

    assert result.outcome == UnlockOutcome.ALREADY_UNLOCKED
    assert GateUnlock.objects.get(enrollment=waiting_enrollment).source == GateUnlockSource.API
    assert next_contents(waiting_enrollment) == ["Paid lesson"]


def test_an_ended_enrollment_cannot_be_unlocked(gate_course, waiting_enrollment):
    waiting_enrollment.status = EnrollmentStatus.DEACTIVATED
    waiting_enrollment.deactivation_reason = DeactivationReason.CANCELED
    waiting_enrollment.save()

    result = unlock_gate(waiting_enrollment, gate_course.gate_content, GateUnlockSource.API)

    assert result.outcome == UnlockOutcome.NOT_UNLOCKABLE
    assert not GateUnlock.objects.exists()


def test_unlocking_a_gate_that_ends_the_course_graduates_the_learner(gate_course, waiting_enrollment):
    gate_course.paid_lesson.is_published = False
    gate_course.paid_lesson.save()

    unlock_gate(waiting_enrollment, gate_course.gate_content, GateUnlockSource.ADMIN)

    waiting_enrollment.refresh_from_db()
    assert waiting_enrollment.status == EnrollmentStatus.COMPLETED


def test_only_gate_content_of_the_enrollments_course_can_be_unlocked(gate_course, active_enrollment):
    with pytest.raises(ValueError):
        unlock_gate(active_enrollment, gate_course.welcome, GateUnlockSource.API)


# ── timing out ───────────────────────────────────────────────────────────────


def expire_now(enrollment):
    delivery = waiting_gate_delivery(enrollment)
    delivery.valid_until = timezone.now() - timedelta(minutes=1)
    delivery.save()
    return delivery


def test_a_timed_out_gate_deactivates_the_enrollment(gate_course, waiting_enrollment, job_factory):
    gate_course.gate.timeout_days = 7
    gate_course.gate.save()
    expire_now(waiting_enrollment)
    mail.outbox.clear()

    DeactivateInactiveEnrollmentsJob().run()

    waiting_enrollment.refresh_from_db()
    assert waiting_enrollment.status == EnrollmentStatus.DEACTIVATED
    assert waiting_enrollment.deactivation_reason == DeactivationReason.GATE_EXPIRED
    assert len(mail.outbox) == 1
    assert "Payment" in mail.outbox[0].body


def test_a_timed_out_gate_set_to_continue_lets_the_learner_through(gate_course, waiting_enrollment):
    gate_course.gate.timeout_days = 7
    gate_course.gate.timeout_action = GateTimeoutAction.CONTINUE
    gate_course.gate.save()
    expire_now(waiting_enrollment)

    DeactivateInactiveEnrollmentsJob().run()

    waiting_enrollment.refresh_from_db()
    assert waiting_enrollment.status == EnrollmentStatus.ACTIVE
    assert GateUnlock.objects.get(enrollment=waiting_enrollment).source == GateUnlockSource.TIMEOUT
    assert next_contents(waiting_enrollment) == ["Paid lesson"]


def test_a_gate_without_a_timeout_never_ends_the_wait(waiting_enrollment):
    DeactivateInactiveEnrollmentsJob().run()

    waiting_enrollment.refresh_from_db()
    assert waiting_enrollment.status == EnrollmentStatus.ACTIVE
    assert waiting_gate_delivery(waiting_enrollment) is not None


def test_expire_gate_leaves_an_ended_enrollment_alone(gate_course, waiting_enrollment):
    delivery = expire_now(waiting_enrollment)
    Enrollment.objects.filter(id=waiting_enrollment.id).update(status=EnrollmentStatus.COMPLETED)

    gate_service.expire_gate(delivery)

    waiting_enrollment.refresh_from_db()
    assert waiting_enrollment.status == EnrollmentStatus.COMPLETED


# ── the learner cap ──────────────────────────────────────────────────────────


def test_learners_waiting_at_a_gate_do_not_count_toward_the_cap(settings, gate_course, waiting_enrollment):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    organization = gate_course.course.organization

    assert organization.active_learner_count() == 0
    assert organization.can_enroll_learner()

    progressing = Learner.objects.create(email="progressing@example.com", organization=organization)
    Enrollment.objects.create(learner=progressing, course=gate_course.course, status=EnrollmentStatus.ACTIVE)

    assert organization.active_learner_count() == 1
    assert not organization.can_enroll_learner()


def test_is_waiting_at_gate_marks_only_held_enrollments(gate_course, waiting_enrollment):
    other = Enrollment.objects.create(
        learner=Learner.objects.create(email="other@example.com", organization_id=1),
        course=gate_course.course,
        status=EnrollmentStatus.ACTIVE,
    )

    waiting = dict(Enrollment.objects.annotate(waiting=is_waiting_at_gate()).values_list("id", "waiting"))

    assert waiting == {waiting_enrollment.id: True, other.id: False}
