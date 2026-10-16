"""Choosing how a course's enrollments are confirmed, and editing the emails around it."""

import json

import pytest
from django.urls import reverse

from django_email_learning.models import Course, CourseContent, EnrollmentConfirmation, Gate


def course_url(course):
    return reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": course.organization_id, "course_id": course.id},
    )


def update(client, course, **payload):
    return client.post(course_url(course), json.dumps({"image": "SKIP", **payload}), content_type="application/json")


def test_a_course_starts_confirmed_by_link_with_the_default_emails(superadmin_client, course):
    body = superadmin_client.get(course_url(course)).json()

    assert body["enrollment_confirmation"] == "link"
    assert body["welcome_email_subject"] == "Enrollment Verified"
    assert body["welcome_email_body"] == body["default_welcome_email_body"]
    assert "{{ course_title }}" in body["welcome_email_body"]
    assert body["welcome_email_customized"] is False
    assert body["enrollment_email_body"] == body["default_enrollment_email_body"]


def test_gating_enrollments(superadmin_client, course):
    response = update(superadmin_client, course, enrollment_confirmation="gate", enrollment_gate_key="payment")

    assert response.status_code == 200
    course.refresh_from_db()
    assert course.enrollment_confirmation == EnrollmentConfirmation.GATE
    assert course.enrollment_gate_key == "payment"


def test_gated_enrollments_need_a_key(superadmin_client, course):
    response = update(superadmin_client, course, enrollment_confirmation="gate")

    assert response.status_code == 400
    course.refresh_from_db()
    assert course.enrollment_confirmation == EnrollmentConfirmation.LINK


@pytest.mark.parametrize("key", ["has space", "slash/es"])
def test_the_enrollment_gate_key_must_be_a_slug(superadmin_client, course, key):
    response = update(superadmin_client, course, enrollment_confirmation="gate", enrollment_gate_key=key)

    assert response.status_code == 400


def test_the_enrollment_gate_key_cannot_clash_with_a_content_gate(superadmin_client, gate_course):
    course = gate_course.course

    response = update(superadmin_client, course, enrollment_confirmation="gate", enrollment_gate_key="payment")

    assert response.status_code == 400
    assert "payment" in response.json()["error"]


def test_a_content_gate_cannot_take_the_enrollment_gate_key(course):
    course.enrollment_confirmation = EnrollmentConfirmation.GATE
    course.enrollment_gate_key = "payment"
    course.save()
    gate = Gate.objects.create(title="Payment", key="payment")

    with pytest.raises(Exception, match="enrollment gate"):
        CourseContent.objects.create(course=course, priority=1, type="gate", gate=gate, waiting_period=3600)


def test_editing_the_emails(superadmin_client, course):
    response = update(
        superadmin_client,
        course,
        welcome_email_subject="Welcome to {{ course_title }}",
        welcome_email_body="<p>Hello</p><script>alert(1)</script>",
        enrollment_email_body="<p>Pay first</p>",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["welcome_email_subject"] == "Welcome to {{ course_title }}"
    assert body["welcome_email_body"] == "<p>Hello</p>alert(1)"
    assert body["welcome_email_customized"] is True
    assert body["enrollment_email_body"] == "<p>Pay first</p>"
    # The subject left out keeps following the default.
    assert body["enrollment_email_subject"] == body["default_enrollment_email_subject"]


def test_null_restores_the_default_email(superadmin_client, course):
    course.welcome_email_subject = "Custom"
    course.welcome_email_body = "<p>Custom</p>"
    course.save()

    response = update(superadmin_client, course, welcome_email_subject=None, welcome_email_body=None)

    body = response.json()
    assert body["welcome_email_customized"] is False
    assert body["welcome_email_body"] == body["default_welcome_email_body"]
    course.refresh_from_db()
    assert course.welcome_email_body is None


def test_leaving_the_emails_out_keeps_them(superadmin_client, course):
    course.welcome_email_body = "<p>Custom</p>"
    course.save()

    update(superadmin_client, course, title="Renamed")

    assert Course.objects.get(id=course.id).welcome_email_body == "<p>Custom</p>"
