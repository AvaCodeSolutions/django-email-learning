from django_email_learning.models import Enrollment
from django.core.exceptions import ValidationError
from freezegun import freeze_time
from unittest.mock import patch, call
import pytest


def immediately(func):
    func()


def test_enrollment_minimal_save(learner, course):
    enrollment = Enrollment.objects.create(learner=learner, course=course)
    fetched_enrollment = Enrollment.objects.get(id=enrollment.id)
    assert fetched_enrollment.learner == learner
    assert fetched_enrollment.course == course
    assert fetched_enrollment.enrolled_at is not None
    assert fetched_enrollment.status == "unverified"
    assert fetched_enrollment.activation_code is not None
    assert len(fetched_enrollment.activation_code) == 6


@pytest.mark.parametrize(
    "initial_status,new_status,deactivation_reason",
    [
        ("unverified", "active", None),
        ("active", "completed", None),
        ("unverified", "deactivated", "canceled"),
        ("active", "deactivated", "canceled"),
    ],
)
def test_update_valid_status(
    db, learner, course, initial_status, new_status, deactivation_reason
):
    enrollment = Enrollment.objects.create(
        learner=learner, course=course, status=initial_status
    )
    enrollment.status = new_status
    enrollment.deactivation_reason = deactivation_reason
    enrollment.save()


@pytest.mark.parametrize(
    "initial_status,new_status,deactivation_reason,new_deactivation_reason",
    [
        ("completed", "active", None, None),
        ("deactivated", "active", "canceled", None),
        ("completed", "unverified", None, None),
        ("deactivated", "unverified", "canceled", None),
        ("completed", "deactivated", None, "canceled"),
        ("deactivated", "completed", "canceled", None),
    ],
)
def test_update_invalid_status(
    db,
    learner,
    course,
    initial_status,
    new_status,
    deactivation_reason,
    new_deactivation_reason,
):
    enrollment = Enrollment.objects.create(
        learner=learner,
        course=course,
        status=initial_status,
        deactivation_reason=deactivation_reason,
    )
    enrollment.status = new_status
    enrollment.deactivation_reason = new_deactivation_reason
    with pytest.raises(ValidationError) as exc_info:
        enrollment.save()
    assert f"Invalid status transition from {initial_status} to {new_status}." in str(
        exc_info.value
    )


def test_deactivation_reason_set_only_when_deactivated(db, learner, course):
    enrollment = Enrollment.objects.create(
        learner=learner, course=course, status="active"
    )
    enrollment.deactivation_reason = "Violated terms"
    with pytest.raises(ValidationError) as exc_info:
        enrollment.save()
    assert "Deactivation reason must be null unless status is 'deactivated'." in str(
        exc_info.value
    )


def test_learner_required_field(db, course):
    with pytest.raises(ValidationError) as exc_info:
        Enrollment.objects.create(course=course)
    assert "learner" in str(exc_info.value)


def test_course_required_field(db, learner):
    with pytest.raises(ValidationError) as exc_info:
        Enrollment.objects.create(learner=learner)
    assert "course" in str(exc_info.value)


@pytest.mark.parametrize("existing_status", ["unverified", "active", "completed"])
def test_unique_active_enrollment_constraint(db, learner, course, existing_status):
    Enrollment.objects.create(learner=learner, course=course, status=existing_status)
    with pytest.raises(ValidationError) as exc_info:
        Enrollment.objects.create(learner=learner, course=course, status="unverified")
    assert "unique_active_enrollment" in str(exc_info.value)


def test_unique_active_enrollment_allows_deactivated(db, learner, course):
    Enrollment.objects.create(
        learner=learner,
        course=course,
        status="deactivated",
        deactivation_reason="canceled",
    )
    enrollment = Enrollment.objects.create(
        learner=learner, course=course, status="unverified"
    )
    assert enrollment.id is not None


@pytest.mark.parametrize("reason", ["canceled", "blocked", "failed", "inactive"])
def test_deactivated_valid_reason(db, learner, course, reason):
    enrollment = Enrollment.objects.create(
        learner=learner, course=course, status="deactivated", deactivation_reason=reason
    )
    assert enrollment.id is not None


def test_deactivated_invalid_reason(db, learner, course):
    with pytest.raises(ValidationError) as exc_info:
        Enrollment.objects.create(
            learner=learner,
            course=course,
            status="deactivated",
            deactivation_reason="invalid_reason",
        )
    assert "Value 'invalid_reason' is not a valid choice" in str(exc_info.value)


def test_deactivation_reason_null_when_not_deactivated(db, learner, course):
    with pytest.raises(ValidationError) as exc_info:
        Enrollment.objects.create(
            learner=learner,
            course=course,
            status="active",
            deactivation_reason="canceled",
        )
    assert "Deactivation reason must be null unless status is 'deactivated'." in str(
        exc_info.value
    )


def test_schedule_first_content_delivery_creates_delivery_and_schedule(
    db, enrollment, course_lesson_content
):
    course_lesson_content.waiting_period = 3600  # 1 hour
    course_lesson_content.save()

    with freeze_time("2024-01-01 10:00:00"):
        enrollment.schedule_first_content_delivery()

        deliveries = enrollment.content_deliveries.all()
        assert deliveries.count() == 1
        delivery = deliveries.first()
        assert delivery.course_content == course_lesson_content

        schedules = delivery.delivery_schedules.all()
        assert schedules.count() == 1
        schedule = schedules.first()
        assert schedule.time.isoformat() == "2024-01-01T11:00:00+00:00"  # 1 hour later


@patch("django_email_learning.models.DeliverySchedule.objects.create")
def test_schedule_first_content_delivery_atomic_transaction(
    mock_create_schedule, db, enrollment, course_lesson_content
):
    mock_create_schedule.side_effect = Exception("Failed to create schedule")
    course_lesson_content.waiting_period = 3600  # 1 hour
    course_lesson_content.save()

    with freeze_time("2024-01-01 10:00:00"):
        # Simulate failure to create schedule by not adding any schedule after delivery creation
        with pytest.raises(Exception):
            enrollment.schedule_first_content_delivery()

        deliveries = enrollment.content_deliveries.all()
        assert (
            deliveries.count() == 0
        )  # Delivery should be deleted if no schedule created


# ---------------------------------------------------------------------------
# graduate — send_certificate
# ---------------------------------------------------------------------------


@patch(
    "django_email_learning.models.enrollments.transaction.on_commit",
    side_effect=immediately,
)
@patch(
    "django_email_learning.models.enrollments.Enrollment.send_certificate_form",
    autospec=True,
)
def test_graduate_sends_certificate_when_enabled(
    mock_send, mock_on_commit, active_enrollment
):
    active_enrollment.graduate()
    mock_send.assert_called_once()


@patch(
    "django_email_learning.models.enrollments.transaction.on_commit",
    side_effect=immediately,
)
@patch(
    "django_email_learning.models.enrollments.Enrollment.send_certificate_form",
    autospec=True,
)
def test_graduate_does_not_send_certificate_when_disabled(
    mock_send, mock_on_commit, active_enrollment
):
    active_enrollment.course.send_certificate = False
    active_enrollment.course.save()
    active_enrollment.graduate()
    mock_send.assert_not_called()
