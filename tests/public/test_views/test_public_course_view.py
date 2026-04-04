import json

from django.urls import reverse

from django_email_learning.models import ExternalReference


def test_course_view_anonymous_client(
    db, anonymous_client, course, course_lesson_content
):
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
    assert (
        response.context["page_title"]
        == response.context["appContext"]["course"]["title"]
    )
    assert response.context["appContext"]["enrollApiUrl"].startswith("http")
    assert (
        response.context["appContext"]["course"]["target_audience"]
        == course.target_audience
    )
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
