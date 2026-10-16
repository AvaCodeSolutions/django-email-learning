import re
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlsplit

from django.core import mail
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from django_email_learning.models import Enrollment, EnrollmentStatus
from django_email_learning.services import jwt_service
from django_email_learning.services.command_models.enroll_command import EnrollCommand

URL = reverse("django_email_learning:personalised:verify_enrollment")


@patch("django_email_learning.personalised.views.VerifyEnrollmentCommand")
def test_verification_valid_token(command, enrollment, anonymous_client):
    token = jwt_service.generate_jwt(
        {
            "enrollment_id": enrollment.id,
            "verification_code": enrollment.activation_code,
        }
    )

    response = anonymous_client.get(f"{URL}?token={token}")

    assert command.return_value.execute.called
    assert response.status_code == 200
    assert "page_title" in response.context
    assert response.context["page_title"] == "Enrollment Verified"


def test_verification_invalid_token(anonymous_client):
    response = anonymous_client.get(f"{URL}?token=invalidtoken")
    assert response.status_code == 400
    assert "The link is not valid." in response.content.decode()


def _verify(anonymous_client, enrollment):
    token = jwt_service.generate_jwt({"enrollment_id": enrollment.id, "verification_code": enrollment.activation_code})
    with patch("django_email_learning.personalised.views.VerifyEnrollmentCommand"):
        return anonymous_client.get(f"{URL}?token={token}")


def test_verified_page_offers_sharing_a_public_course(enrollment, anonymous_client):
    course = enrollment.course
    course.enabled = True
    course.is_public = True
    course.save()
    course.organization.is_public = True
    course.organization.save()

    app_context = _verify(anonymous_client, enrollment).context["appContext"]

    assert app_context["shareUrl"] == course.public_url
    assert app_context["shareTitle"] == course.title
    assert "share_after_enrollment" in app_context["localeMessages"]


def test_verified_page_has_nothing_to_share_for_a_non_public_course(enrollment, anonymous_client):
    course = enrollment.course
    course.enabled = True
    course.is_public = False
    course.save()

    app_context = _verify(anonymous_client, enrollment).context["appContext"]

    assert app_context["shareUrl"] is None
    assert app_context["shareTitle"] is None


# # TODO: Add more tests for various scenarios


def test_a_verification_link_still_works_weeks_later(course, course_lesson_content, anonymous_client):
    """The link used to expire after an hour, so learners who opened the email later never got in."""
    course.enabled = True
    course.save()
    EnrollCommand(email="late@example.com", course_slug=course.slug, organization_id=1).execute()
    [link] = re.findall(r"https?://\S+\?token=[\w.-]+", mail.outbox[0].body)

    with freeze_time(timezone.now() + timedelta(days=30)):
        parts = urlsplit(link)
        response = anonymous_client.get(f"{parts.path}?{parts.query}")

    assert response.status_code == 200
    assert Enrollment.objects.get(learner__email="late@example.com").status == EnrollmentStatus.ACTIVE
