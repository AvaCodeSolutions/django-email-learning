"""How an enrollment waiting at, and let through, its course's enrollment gate shows on the learners page."""

import json
import re
from urllib.parse import urlsplit

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse

from django_email_learning.models import (
    ApiKeyScope,
    Enrollment,
    EnrollmentConfirmation,
    GateUnlockSource,
)
from django_email_learning.services.command_models.enroll_command import EnrollCommand
from django_email_learning.services.enrollment_confirmation_service import confirm_gated_enrollment
from django_email_learning.services.enrollment_emails import enrollment_email_open_url
from tests.organization_api.conftest import make_key


@pytest.fixture
def gated_course(course, course_lesson_content):
    course.enabled = True
    course.enrollment_confirmation = EnrollmentConfirmation.GATE
    course.enrollment_gate_key = "payment"
    course.save()
    return course


def detail(client, enrollment):
    url = reverse(
        "django_email_learning:api_platform:enrollments_detail",
        kwargs={"organization_id": 1, "enrollment_id": enrollment.id},
    )
    return client.get(url).json()


def events_of(client, enrollment, event_type):
    return [event for event in detail(client, enrollment)["events"] if event["type"] == event_type]


def pixel_path(url):
    return urlsplit(url).path


def test_the_learners_list_shows_an_enrollment_waiting_at_the_enrollment_gate(
    org_admin_client, gated_course, enrollment
):
    url = reverse("django_email_learning:api_platform:learners_list", kwargs={"organization_id": 1})

    [item] = org_admin_client.get(f"{url}?course_id={gated_course.id}").json()["items"]

    assert item["enrollment_status"] == "unverified"
    assert item["enrollment_awaiting_confirmation"] is True


def test_an_unverified_enrollment_in_a_course_confirmed_by_link_is_not_waiting(org_admin_client, course, enrollment):
    url = reverse("django_email_learning:api_platform:learners_list", kwargs={"organization_id": 1})

    [item] = org_admin_client.get(f"{url}?course_id={course.id}").json()["items"]

    assert item["enrollment_awaiting_confirmation"] is False


def test_an_admin_confirmation_shows_who_confirmed_it(org_admin_client, gated_course, enrollment, users):
    confirm_url = reverse(
        "django_email_learning:api_platform:enrollment_confirm",
        kwargs={"organization_id": 1, "enrollment_id": enrollment.id},
    )
    org_admin_client.post(confirm_url)

    [event] = events_of(org_admin_client, enrollment, "enrollment_confirmed")

    enrollment.refresh_from_db()
    assert enrollment.confirmation_source == GateUnlockSource.ADMIN
    assert event["event_data"]["source"] == "admin"
    assert event["event_data"]["confirmed_by"] == enrollment.confirmed_by.get_username()
    # Nothing was verified, so the timeline doesn't say it was.
    assert events_of(org_admin_client, enrollment, "verified") == []


def test_an_api_confirmation_records_the_key(org_admin_client, gated_course, enrollment):
    api_client = Client()
    auth = {"HTTP_AUTHORIZATION": f"Bearer {make_key(scopes=[ApiKeyScope.ENROLLMENTS_UPDATE])}"}
    api_client.post(
        reverse("django_email_learning:api_v1:enrollment_unlock", kwargs={"enrollment_id": enrollment.id}),
        data=json.dumps({"gate": "payment"}),
        content_type="application/json",
        **auth,
    )

    enrollment.refresh_from_db()
    assert enrollment.confirmation_source == GateUnlockSource.API
    assert enrollment.confirmation_api_key is not None
    [event] = events_of(org_admin_client, enrollment, "enrollment_confirmed")
    assert event["event_data"] == {"source": "api", "confirmed_by": None}


def test_a_learner_verification_still_shows_as_verified(org_admin_client, active_enrollment):
    assert len(events_of(org_admin_client, active_enrollment, "verified")) == 1
    assert events_of(org_admin_client, active_enrollment, "enrollment_confirmed") == []


@pytest.mark.parametrize(
    ("confirmation", "email"),
    [(EnrollmentConfirmation.LINK, "verification"), (EnrollmentConfirmation.GATE, "enrollment")],
)
def test_opening_the_first_email_shows_in_the_timeline(org_admin_client, gated_course, confirmation, email):
    gated_course.enrollment_confirmation = confirmation
    gated_course.save()
    EnrollCommand(email="new@example.com", course_slug=gated_course.slug, organization_id=1).execute()
    enrollment = Enrollment.objects.get(learner__email="new@example.com")

    [sent] = mail.outbox
    html = sent.alternatives[0][0]
    [pixel] = re.findall(r'<img src="([^"]+/track/enrollment-open/[^"]+)"', html)
    assert pixel == enrollment_email_open_url(enrollment)

    response = Client().get(pixel_path(pixel))
    assert response["Content-Type"] == "image/gif"

    [event] = events_of(org_admin_client, enrollment, "enrollment_email_opened")
    assert event["event_data"] == {"email": email}


def test_only_the_first_open_is_recorded(gated_course, enrollment):
    pixel = pixel_path(enrollment_email_open_url(enrollment))
    Client().get(pixel)
    enrollment.refresh_from_db()
    first_open = enrollment.enrollment_email_opened_at

    Client().get(pixel)

    enrollment.refresh_from_db()
    assert first_open is not None
    assert enrollment.enrollment_email_opened_at == first_open


def test_a_forged_token_still_gets_the_pixel_and_records_nothing(enrollment):
    url = reverse("django_email_learning:personalised:track_enrollment_email_open", kwargs={"token": "forged"})

    response = Client().get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "image/gif"
    enrollment.refresh_from_db()
    assert enrollment.enrollment_email_opened_at is None


def test_confirming_after_opening_keeps_the_open(gated_course, enrollment):
    Client().get(pixel_path(enrollment_email_open_url(enrollment)))

    confirm_gated_enrollment(enrollment, GateUnlockSource.API)

    enrollment.refresh_from_db()
    assert enrollment.enrollment_email_opened_at is not None


def test_the_open_names_the_email_that_was_sent_even_after_the_course_switches(org_admin_client, gated_course):
    gated_course.enrollment_confirmation = EnrollmentConfirmation.LINK
    gated_course.save()
    EnrollCommand(email="new@example.com", course_slug=gated_course.slug, organization_id=1).execute()
    enrollment = Enrollment.objects.get(learner__email="new@example.com")
    assert enrollment.enrollment_email_type == "verification"

    gated_course.enrollment_confirmation = EnrollmentConfirmation.GATE
    gated_course.save()
    Client().get(pixel_path(enrollment_email_open_url(enrollment)))

    [event] = events_of(org_admin_client, enrollment, "enrollment_email_opened")
    assert event["event_data"] == {"email": "verification"}


def test_an_empty_enrollment_email_records_no_email_sent(gated_course):
    gated_course.enrollment_email_body = ""
    gated_course.save()

    EnrollCommand(email="new@example.com", course_slug=gated_course.slug, organization_id=1).execute()

    assert Enrollment.objects.get(learner__email="new@example.com").enrollment_email_type is None
