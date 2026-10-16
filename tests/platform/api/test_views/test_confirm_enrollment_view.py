import pytest
from django.core import mail
from django.urls import reverse

from django_email_learning.models import EnrollmentConfirmation, EnrollmentStatus


def get_url(enrollment_id, organization_id=1):
    return reverse(
        "django_email_learning:api_platform:enrollment_confirm",
        kwargs={"organization_id": organization_id, "enrollment_id": enrollment_id},
    )


@pytest.fixture
def gated_enrollment(course, course_lesson_content, enrollment):
    course.enrollment_confirmation = EnrollmentConfirmation.GATE
    course.enrollment_gate_key = "payment"
    course.save()
    return enrollment


def test_an_admin_confirms_a_gated_enrollment(org_admin_client, gated_enrollment):
    response = org_admin_client.post(get_url(gated_enrollment.id))

    assert response.status_code == 200
    assert response.json() == {"status": "confirmed", "enrollment_status": "active"}
    gated_enrollment.refresh_from_db()
    assert gated_enrollment.status == EnrollmentStatus.ACTIVE
    assert len(mail.outbox) == 1


@pytest.mark.parametrize("client", ["viewer", "editor", "instructor"], indirect=True)
def test_confirming_is_forbidden_for_non_admins(client, gated_enrollment):
    response = client.post(get_url(gated_enrollment.id))

    assert response.status_code == 403
    gated_enrollment.refresh_from_db()
    assert gated_enrollment.status == EnrollmentStatus.UNVERIFIED


def test_an_admin_verifies_an_enrollment_in_a_course_confirmed_by_link(
    org_admin_client, course, course_lesson_content, enrollment
):
    response = org_admin_client.post(get_url(enrollment.id))

    assert response.status_code == 200
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.ACTIVE
    assert enrollment.confirmation_source == "admin"
    assert enrollment.confirmed_by is not None
    assert [email.subject for email in mail.outbox] == ["Enrollment Verified"]

    url = reverse(
        "django_email_learning:api_platform:enrollments_detail",
        kwargs={"organization_id": 1, "enrollment_id": enrollment.id},
    )
    events = {event["type"]: event for event in org_admin_client.get(url).json()["events"]}
    assert events["enrollment_confirmed"]["event_data"]["source"] == "admin"
    assert "verified" not in events


def test_an_unknown_enrollment_is_not_found(org_admin_client, db):
    assert org_admin_client.post(get_url(999)).status_code == 404


def test_the_enrollment_detail_says_whether_the_course_is_gated(org_admin_client, gated_enrollment):
    url = reverse(
        "django_email_learning:api_platform:enrollments_detail",
        kwargs={"organization_id": 1, "enrollment_id": gated_enrollment.id},
    )

    assert org_admin_client.get(url).json()["course"]["is_enrollment_gated"] is True
