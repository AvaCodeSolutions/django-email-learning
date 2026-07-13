import json

import pytest
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from django_email_learning.models import Enrollment, EnrollmentStatus, ExternalReference, Learner


@pytest.fixture
def tos_settings(request):
    with override_settings(
        DJANGO_EMAIL_LEARNING={
            **settings.DJANGO_EMAIL_LEARNING,
            "TERMS_OF_SERVICE_URL": request.param,
        }
    ):
        yield settings.DJANGO_EMAIL_LEARNING["TERMS_OF_SERVICE_URL"]


def test_course_view_anonymous_client(db, anonymous_client, course, course_lesson_content):
    course.enabled = True
    course.target_audience = "Beginners with no prior programming experience."
    course.save()
    ExternalReference.objects.create(
        course=course,
        name="Documentation",
        url="https://django-email-learning.readthedocs.io/",
    )

    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": course.slug},
    )
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert response.context["appContext"]["course"]["id"] == course.id
    assert response.context["page_title"] == response.context["appContext"]["course"]["title"]
    assert response.context["appContext"]["enrollApiUrl"].startswith("http")
    assert response.context["appContext"]["enrollmentOpen"] is True
    assert response.context["appContext"]["course"]["target_audience"] == course.target_audience
    assert response.context["appContext"]["course"]["external_references"] == [
        {
            "name": "Documentation",
            "url": "https://django-email-learning.readthedocs.io/",
        }
    ]
    assert response.context["appContext"]["course"]["lessons"] == ["Sample Lesson"]

    json_ld = json.loads(response.context["json_ld"])
    assert json_ld["@type"] == "Course"
    assert json_ld["name"] == course.title
    assert json_ld["audience"]["audienceType"] == course.target_audience
    assert json_ld["teaches"] == ["Sample Lesson"]


def test_course_view_json_ld_escapes_script_tag_in_description(db, anonymous_client, course):
    course.enabled = True
    course.description = "Nice course</script><script>alert(document.cookie)</script>"
    course.save()

    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": course.slug},
    )
    response = anonymous_client.get(url)

    assert response.status_code == 200
    raw_json_ld = response.context["json_ld"]
    assert "</script>" not in raw_json_ld
    # Still valid, parseable JSON that round-trips back to the original value.
    assert json.loads(raw_json_ld)["description"] == course.description


def test_course_view_enrollment_closed_when_cap_reached(db, anonymous_client, course, settings):
    course.enabled = True
    course.save()
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    learner = Learner.objects.create(email="learner@example.com", organization=course.organization)
    Enrollment.objects.create(learner=learner, course=course, status=EnrollmentStatus.ACTIVE)

    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": course.slug},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 200
    assert response.context["appContext"]["enrollmentOpen"] is False


def test_course_view_excludes_disabled_course(db, anonymous_client, course):
    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": course.slug},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 404


def test_course_view_non_existent_course(db, anonymous_client):
    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": "missing-course"},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "tos_settings",
    ["https://example.com/terms", None],
    indirect=True,
)
def test_course_view_includes_terms_of_service_url_when_configured(db, anonymous_client, course, tos_settings):
    course.enabled = True
    course.save()

    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": course.slug},
    )
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert response.context["appContext"]["termsOfServiceUrl"] == tos_settings


def test_course_view_excludes_non_public_course(db, anonymous_client, course):
    course.enabled = True
    course.is_public = False
    course.save()

    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": course.slug},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 404


def test_course_view_excludes_course_from_non_public_organization(db, anonymous_client, course):
    course.enabled = True
    course.save()

    # Make the organization non-public
    course.organization.is_public = False
    course.organization.save()

    url = reverse(
        "django_email_learning:public:course_view",
        kwargs={"organization_id": 1, "course_slug": course.slug},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 404
