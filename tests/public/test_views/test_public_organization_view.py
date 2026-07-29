import json

from django.urls import reverse

from django_email_learning.models import Enrollment, EnrollmentStatus, Learner, Organization


def test_organization_view_anonymous_client(db, anonymous_client):
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)
    assert response.status_code == 200
    assert response.context["appContext"]["organization"]["id"] == 1
    assert response.context["page_title"] == response.context["appContext"]["organization"]["name"]
    assert response.context["appContext"]["enrollApiUrl"].startswith("http")
    assert response.context["appContext"]["enrollmentOpen"] is True

    # No course added yet, so courses list should be empty
    assert len(response.context["appContext"]["organization"]["courses"]) == 0


def test_organization_view_includes_brand_color(db, anonymous_client):
    Organization.objects.filter(id=1).update(brand_color="#654321")
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)
    assert response.status_code == 200
    assert response.context["appContext"]["organization"]["brand_color"] == "#654321"


def test_organization_view_enrollment_closed_when_cap_reached(anonymous_client, settings, course):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "LEARNERS": {"MAX_LEARNERS_PER_ORGANIZATION": 1},
    }
    learner = Learner.objects.create(email="learner@example.com", organization=Organization.objects.get(id=1))
    Enrollment.objects.create(learner=learner, course=course, status=EnrollmentStatus.ACTIVE)
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)
    assert response.status_code == 200
    assert response.context["appContext"]["enrollmentOpen"] is False


def test_organization_view_anonymous_client_with_courses(db, anonymous_client, course):
    course.enabled = True
    course.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert len(response.context["appContext"]["organization"]["courses"]) == 1


def test_organization_view_non_existent_organization(db, anonymous_client):
    url = reverse(
        "django_email_learning:public:organization_view",
        kwargs={"organization_id": 999},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 404


def test_organization_view_excludes_disabled_courses(db, anonymous_client, course):
    course.enabled = False
    course.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert len(response.context["appContext"]["organization"]["courses"]) == 0


def test_organization_view_excludes_non_public_courses(db, anonymous_client, course):
    course.enabled = True
    course.is_public = False
    course.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert len(response.context["appContext"]["organization"]["courses"]) == 0


def test_organization_view_json_ld_escapes_script_tag_in_course_description(db, anonymous_client, course):
    course.enabled = True
    course.description = "Nice course</script><script>alert(document.cookie)</script>"
    course.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})

    response = anonymous_client.get(url)

    assert response.status_code == 200
    raw_json_ld = response.context["json_ld"]
    assert "</script>" not in raw_json_ld
    assert json.loads(raw_json_ld)["itemListElement"][0]["description"] == course.description


def test_organization_view_retuns_404_for_non_public_organization(db, anonymous_client, course):
    organization = course.organization
    organization.is_public = False
    organization.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)

    assert response.status_code == 404
