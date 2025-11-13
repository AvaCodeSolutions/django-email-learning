from django.urls import reverse
from django_email_learning.models import Organization
from django_email_learning.models import Course
import json
import uuid
import pytest


def get_url(organization_id: int) -> str:
    return reverse(
        "django_email_learning:api:course_view",
        kwargs={"organization_id": organization_id},
    )


def test_create_course_success(superadmin_client):
    payload = valid_create_course_payload()
    response = superadmin_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["title"] == payload["title"]
    assert response.json()["slug"] == payload["slug"]
    assert response.json()["description"] == payload["description"]
    assert response.json()["organization_id"] == 1
    assert response.json()["imap_connection_id"] is None


def test_create_course_not_authenticated(anonymous_client):
    payload = valid_create_course_payload()
    response = anonymous_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


@pytest.mark.parametrize(
    "client,expected_status",
    [("editor", 201), ("platform_admin", 201), ("viewer", 403)],
    indirect=["client"],
)
def test_create_course_user_access(client, expected_status):
    payload = json.dumps(
        valid_create_course_payload(uuid.uuid4().hex, uuid.uuid4().hex)
    )
    response = client.post(get_url(1), payload, content_type="application/json")
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "Only Title"},
        {"slug": "only-slug"},
        {"title": "", "slug": "valid-slug"},
        {"title": "Valid Title", "slug": ""},
        {"title": "Valid Title", "slug": "valid-slug", "description": 123},
        {
            "title": "Valid Title",
            "slug": "valid-slug",
            "imap_connection_id": "not-an-integer",
        },
    ],
)
def test_create_course_invalid_payload(superadmin_client, payload):
    response = superadmin_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_create_course_existing_slug(superadmin_client):
    payload = valid_create_course_payload(slug="existing-slug")
    response1 = superadmin_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response1.status_code == 201

    response2 = superadmin_client.post(
        get_url(1), json.dumps(payload), content_type="application/json"
    )
    assert response2.status_code == 409
    assert "error" in response2.json()


def test_platform_admin_can_create_only_for_its_organization(platform_admin_client):
    payload = valid_create_course_payload()
    url = get_url(2)  # organization_id=2 which platform_admin doesn't belong to
    response = platform_admin_client.post(
        url, json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 403
    assert response.json() == {"error": "Forbidden"}


def test_get_course_return_empty_list_when_no_course(superadmin_client):
    response = superadmin_client.get(get_url(1))
    assert response.status_code == 200
    assert response.json() == {"courses": []}


@pytest.fixture()
def create_courses(superadmin_client):
    Organization.objects.create(pk=2, name="Organization 2")
    org_1_url = get_url(1)
    org_2_url = get_url(2)

    # Creating courses in the default organization
    superadmin_client.post(
        org_1_url,
        json.dumps(valid_create_course_payload(title="org_1:course_1", slug="slug_1")),
        content_type="application/json",
    )
    superadmin_client.post(
        org_1_url,
        json.dumps(valid_create_course_payload(title="org_1:course_2", slug="slug_2")),
        content_type="application/json",
    )

    # Creating courses in the new organization
    superadmin_client.post(
        org_2_url,
        json.dumps(valid_create_course_payload(title="org_2:course_1", slug="slug_1")),
        content_type="application/json",
    )


def test_get_courses_return_only_courses_of_organization(
    create_courses, superadmin_client
):
    org_1_url = get_url(1)
    org_2_url = get_url(2)

    # Chek get courses for first organization
    response = superadmin_client.get(org_1_url)
    assert response.status_code == 200
    assert len(response.json()["courses"]) == 2
    assert response.json()["courses"][0]["id"] is not None
    assert response.json()["courses"][1]["id"] is not None
    assert isinstance(response.json()["courses"][0]["id"], int)
    assert response.json()["courses"][0]["title"] == "org_1:course_1"
    assert response.json()["courses"][0]["slug"] == "slug_1"
    assert response.json()["courses"][0]["organization_id"] == 1
    assert response.json()["courses"][1]["title"] == "org_1:course_2"
    assert response.json()["courses"][1]["organization_id"] == 1

    # Chek get courses for second organization
    response = superadmin_client.get(org_2_url)
    assert response.status_code == 200
    assert "courses" in response.json()
    assert isinstance(response.json()["courses"], list)
    assert len(response.json()["courses"]) == 1
    assert isinstance(response.json()["courses"][0]["id"], int)
    assert response.json()["courses"][0]["title"] == "org_2:course_1"
    assert response.json()["courses"][0]["slug"] == "slug_1"
    assert response.json()["courses"][0]["organization_id"] == 2


def test_get_courses_user_access(
    create_courses, platform_admin_client, anonymous_client
):
    org_1_url = get_url(1)
    org_2_url = get_url(2)

    # User from other organizations don't have access
    response = platform_admin_client.get(org_2_url)
    assert response.status_code == 403

    response = platform_admin_client.get(org_1_url)
    assert response.status_code == 200

    # Not accessible for unauthorised users
    response = anonymous_client.get(org_1_url)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "enabled,title,length",
    [
        ("true", "org_1:course_2", 1),
        ("false", "org_1:course_1", 1),
        ("invalid", None, 2),
    ],
)
def test_get_courses_filter_by_enabled(
    create_courses, superadmin_client, enabled, title, length
):
    # Enable one of the courses
    course_2 = Course.objects.get(title="org_1:course_2")
    course_2.enabled = True
    course_2.save()
    # course_1 remains disabled by default
    org_1_url = get_url(1)

    response = superadmin_client.get(org_1_url + f"?enabled={enabled}")
    assert response.status_code == 200
    assert len(response.json()["courses"]) == length
    if length == 1:
        assert response.json()["courses"][0]["title"] == title
        assert response.json()["courses"][0]["enabled"] is (enabled == "true")


def test_update_course_success(superadmin_client):
    # First, create a course to update
    create_payload = valid_create_course_payload()
    create_response = superadmin_client.post(
        get_url(1), json.dumps(create_payload), content_type="application/json"
    )
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    # Now, update the created course
    update_payload = valid_update_course_payload()
    update_url = reverse(
        "django_email_learning:api:single_course_view",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(
        update_url, json.dumps(update_payload), content_type="application/json"
    )
    assert update_response.status_code == 200
    assert update_response.json()["id"] == course_id
    assert update_response.json()["title"] == update_payload["title"]
    assert update_response.json()["description"] == update_payload["description"]
    assert update_response.json()["enabled"] == update_payload["enabled"]


def test_slug_change_not_allowed(superadmin_client):
    # First, create a course to update
    create_payload = valid_create_course_payload()
    create_response = superadmin_client.post(
        get_url(1), json.dumps(create_payload), content_type="application/json"
    )
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    # Now, update the created course
    update_payload = valid_update_course_payload(
        title="New Title", description="New Description"
    )
    update_payload["slug"] = "new-slug"  # Attempt to change slug
    update_url = reverse(
        "django_email_learning:api:single_course_view",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(
        update_url, json.dumps(update_payload), content_type="application/json"
    )
    assert update_response.status_code == 400
    assert "error" in update_response.json()


def test_update_course_not_found(superadmin_client):
    update_payload = valid_update_course_payload()
    update_url = reverse(
        "django_email_learning:api:single_course_view",
        kwargs={"organization_id": 1, "course_id": 9999},
    )
    update_response = superadmin_client.post(
        update_url, json.dumps(update_payload), content_type="application/json"
    )
    assert update_response.status_code == 409
    assert "error" in update_response.json()


@pytest.fixture
def sample_course(superadmin_client):
    create_payload = valid_create_course_payload()
    create_response = superadmin_client.post(
        get_url(1), json.dumps(create_payload), content_type="application/json"
    )
    assert create_response.status_code == 201
    return create_response.json()


def test_update_course_reset_imap_connection_conflict(sample_course, superadmin_client):
    course_id = sample_course["id"]
    update_payload = valid_update_course_payload(
        imap_connection_id=1, reset_imap_connection=True
    )
    update_url = reverse(
        "django_email_learning:api:single_course_view",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(
        update_url, json.dumps(update_payload), content_type="application/json"
    )
    assert update_response.status_code == 409
    assert "error" in update_response.json()
    assert (
        update_response.json()["error"]
        == "Cannot set imap_connection_id when reset_imap_connection is True."
    )


def test_viewer_not_allowed_to_delete_course(sample_course, viewer_client):
    url = reverse(
        "django_email_learning:api:single_course_view",
        kwargs={"organization_id": 1, "course_id": sample_course["id"]},
    )
    delete_response = viewer_client.delete(url)
    assert delete_response.status_code == 403


def test_editor_can_delete_course(sample_course, editor_client):
    # Check that we have one course before the delete
    courses = editor_client.get(get_url(1))
    assert len(courses.json().get("courses")) == 1

    url = reverse(
        "django_email_learning:api:single_course_view",
        kwargs={"organization_id": 1, "course_id": sample_course["id"]},
    )
    delete_response = editor_client.delete(url)
    assert delete_response.status_code == 200

    # Check that we don't have any course after the delete
    courses = editor_client.get(get_url(1))
    assert len(courses.json().get("courses")) == 0


def valid_create_course_payload(
    title: str = "Python Course",
    slug: str = "python",
    description: str = "A beginner's course on Python programming.",
) -> dict:
    return {
        "title": title,
        "slug": slug,
        "description": description,
        "imap_connection_id": None,
    }


def valid_update_course_payload(
    title: str = "Updated Python Course",
    description: str = "An updated description for the Python course.",
    imap_connection_id: int = None,
    enabled: bool = True,
    reset_imap_connection: bool = False,
) -> dict:
    return {
        "title": title,
        "description": description,
        "imap_connection_id": imap_connection_id,
        "enabled": enabled,
        "reset_imap_connection": reset_imap_connection,
    }
