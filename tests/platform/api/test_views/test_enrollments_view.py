import json
import uuid

import pytest
from django.urls import reverse

from django_email_learning.models import Enrollment, EnrollmentStatus, Learner


def get_url(organization_id: int, course_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:enrollments_list",
        kwargs={"organization_id": organization_id, "course_id": course_id},
    )


@pytest.mark.parametrize(
    "client,expected_status",
    [
        ("editor", 403),
        ("org_admin", 201),
        ("viewer", 403),
        ("anonymous", 401),
    ],
    indirect=["client"],
)
def test_enrollments_view_post_role_access(client, expected_status, course, course_lesson_content):
    course.enabled = True
    course.save()
    payload = {"learner_email": f"{uuid.uuid4().hex}@example.com"}

    response = client.post(
        get_url(organization_id=1, course_id=course.id),
        json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == expected_status


def test_enrollments_view_post_creates_active_enrollment_and_sends_one_email(
    org_admin_client, course, course_lesson_content, mailoutbox
):
    course.enabled = True
    course.save()
    learner_email = f"{uuid.uuid4().hex}@example.com"

    response = org_admin_client.post(
        get_url(organization_id=1, course_id=course.id),
        json.dumps({"learner_email": learner_email}),
        content_type="application/json",
    )

    assert response.status_code == 201

    enrollment = Enrollment.objects.get(learner__email=learner_email, course_id=course.id)
    assert enrollment.status == EnrollmentStatus.ACTIVE

    assert len(mailoutbox) == 1
    assert learner_email in mailoutbox[0].to


def test_enrollments_view_post_rejects_new_learner_when_cap_reached(
    org_admin_client, course, course_lesson_content, settings
):
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    existing_learner = Learner.objects.create(email="existing@example.com", organization_id=course.organization_id)
    Enrollment.objects.create(learner=existing_learner, course=course, status=EnrollmentStatus.ACTIVE)
    learner_email = f"{uuid.uuid4().hex}@example.com"

    response = org_admin_client.post(
        get_url(organization_id=1, course_id=course.id),
        json.dumps({"learner_email": learner_email}),
        content_type="application/json",
    )

    assert response.status_code == 403
    assert not Learner.objects.filter(email=learner_email).exists()
