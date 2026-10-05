import pytest

from django_email_learning.models import Course, Organization

ORGANIZATION_PATH = "/email_learning/public/@my-organization/"
COURSE_PATH = "/email_learning/public/@my-organization/courses/sample-course/"


@pytest.fixture()
def public_course(course) -> Course:
    course.enabled = True
    course.is_public = True
    course.save()
    return course


def test_organization_page_is_served_at_its_slug(db, anonymous_client):
    response = anonymous_client.get(ORGANIZATION_PATH)
    assert response.status_code == 200
    assert response.context["appContext"]["organization"]["id"] == 1


def test_organization_page_404s_for_an_unknown_slug(db, anonymous_client):
    assert anonymous_client.get("/email_learning/public/@nobody/").status_code == 404


def test_organization_page_404s_for_a_private_organization(db, anonymous_client):
    Organization.objects.filter(id=1).update(is_public=False)
    assert anonymous_client.get(ORGANIZATION_PATH).status_code == 404


def test_organization_id_address_redirects_permanently_to_the_slug(db, anonymous_client):
    response = anonymous_client.get("/email_learning/public/organizations/1/")
    assert response.status_code == 301
    assert response["Location"] == ORGANIZATION_PATH


def test_redirect_keeps_the_query_string(db, anonymous_client):
    response = anonymous_client.get("/email_learning/public/organizations/1/?utm_source=newsletter&x=1")
    assert response.status_code == 301
    assert response["Location"] == f"{ORGANIZATION_PATH}?utm_source=newsletter&x=1"


def test_organization_id_address_does_not_reveal_a_private_organization(db, anonymous_client):
    Organization.objects.filter(id=1).update(is_public=False)
    response = anonymous_client.get("/email_learning/public/organizations/1/")
    assert response.status_code == 404
    assert "Location" not in response


def test_course_page_is_served_at_its_slugs(anonymous_client, public_course):
    response = anonymous_client.get(COURSE_PATH)
    assert response.status_code == 200
    assert response.context["appContext"]["course"]["slug"] == public_course.slug


def test_course_page_404s_under_another_organizations_slug(anonymous_client, public_course):
    Organization.objects.create(name="Acme")
    response = anonymous_client.get(f"/email_learning/public/@acme/courses/{public_course.slug}/")
    assert response.status_code == 404


def test_course_id_address_redirects_permanently_to_the_slug(anonymous_client, public_course):
    response = anonymous_client.get(f"/email_learning/public/organizations/1/courses/{public_course.slug}/")
    assert response.status_code == 301
    assert response["Location"] == COURSE_PATH


def test_course_id_address_404s_for_a_course_that_is_not_public(anonymous_client, public_course):
    Course.objects.filter(pk=public_course.pk).update(is_public=False)
    response = anonymous_client.get(f"/email_learning/public/organizations/1/courses/{public_course.slug}/")
    assert response.status_code == 404


def test_course_id_address_does_not_reveal_a_private_organization(anonymous_client, public_course):
    Organization.objects.filter(id=1).update(is_public=False)
    response = anonymous_client.get(f"/email_learning/public/organizations/1/courses/{public_course.slug}/")
    assert response.status_code == 404


def test_library_route_redirects_to_the_host_route_named_in_settings(anonymous_client, public_course, settings):
    # The test project names its own routes for the public pages, standing in
    # for a host that serves them at the site root.
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "PUBLIC_URL_NAMES": {"organization": "root_organization_page", "course": "root_course_page"},
    }

    organization_response = anonymous_client.get(ORGANIZATION_PATH)
    course_response = anonymous_client.get(COURSE_PATH)

    assert organization_response.status_code == 301
    assert organization_response["Location"] == "/@my-organization/"
    assert course_response.status_code == 301
    assert course_response["Location"] == f"/@my-organization/courses/{public_course.slug}/"


def test_host_route_named_in_settings_serves_the_page(anonymous_client, public_course, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "PUBLIC_URL_NAMES": {"organization": "root_organization_page", "course": "root_course_page"},
    }

    assert anonymous_client.get("/@my-organization/").status_code == 200
    assert anonymous_client.get(f"/@my-organization/courses/{public_course.slug}/").status_code == 200
