from django_email_learning.models import Enrollment
from django.core.exceptions import ValidationError
import pytest


def test_enrollment_minimal_save(learner, course):
    enrollment = Enrollment.objects.create(learner=learner, course=course)
    fetched_enrollment = Enrollment.objects.get(id=enrollment.id)
    assert fetched_enrollment.learner == learner
    assert fetched_enrollment.course == course
    assert fetched_enrollment.enrolled_at is not None
    assert fetched_enrollment.status == "unverified"


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
