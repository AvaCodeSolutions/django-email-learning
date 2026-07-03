import json
import uuid

import pytest
from django.urls import reverse

from django_email_learning.models import (
    Course,
    CourseContent,
    CourseContentType,
    CourseInstructor,
    Lesson,
    Organization,
    OrganizationUser,
)


def get_url(organization_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:courses_list",
        kwargs={"organization_id": organization_id},
    )


def test_create_course_success(superadmin_client):
    payload = valid_create_course_payload()
    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["title"] == payload["title"]
    assert response.json()["slug"] == payload["slug"]
    assert response.json()["description"] == payload["description"]
    assert response.json()["organization_id"] == 1
    assert response.json()["imap_connection_id"] is None
    assert response.json()["language"] == payload["language"]
    assert response.json()["is_rtl"] is False


def test_create_course_with_target_audience_and_external_references(superadmin_client):
    payload = valid_create_course_payload()
    payload["target_audience"] = "Beginners with no prior programming experience."
    payload["external_references"] = [
        {
            "name": "GitHub Repository",
            "url": "https://github.com/AvaCodeSolutions/django-email-learning",
        },
        {
            "name": "Documentation",
            "url": "https://django-email-learning.readthedocs.io/",
        },
    ]
    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    assert response.json()["target_audience"] == payload["target_audience"]
    assert response.json()["external_references"] == payload["external_references"]


def test_create_course_not_authenticated(anonymous_client):
    payload = valid_create_course_payload()
    response = anonymous_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


@pytest.mark.parametrize(
    "client,expected_status",
    [("editor", 201), ("platform_admin", 201), ("viewer", 403)],
    indirect=["client"],
)
def test_create_course_user_access(client, expected_status):
    payload = json.dumps(valid_create_course_payload(uuid.uuid4().hex, uuid.uuid4().hex))
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
    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json()


def test_create_course_existing_slug(superadmin_client):
    payload = valid_create_course_payload(slug="existing-slug")
    response1 = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response1.status_code == 201

    response2 = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response2.status_code == 409
    assert "error" in response2.json()


def test_platform_admin_can_create_only_for_its_organization(platform_admin_client):
    payload = valid_create_course_payload()
    url = get_url(2)  # organization_id=2 which platform_admin doesn't belong to
    response = platform_admin_client.post(url, json.dumps(payload), content_type="application/json")
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


def test_get_courses_return_only_courses_of_organization(create_courses, superadmin_client):
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
    assert "enrollments_count" in response.json()["courses"][0]
    assert "enrollments_count" in response.json()["courses"][1]

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
    assert "enrollments_count" in response.json()["courses"][0]


def test_get_courses_user_access(create_courses, platform_admin_client, anonymous_client):
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
def test_get_courses_filter_by_enabled(create_courses, superadmin_client, enabled, title, length):
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


def test_get_courses_filter_by_is_public(course, superadmin_client):
    # Make one of the courses public
    course.is_public = False
    course.save()

    # Check filtering for public courses
    response = superadmin_client.get(get_url(1) + "?is_public=true")
    assert response.status_code == 200
    assert len(response.json()["courses"]) == 0

    # Check filtering for non public courses
    response = superadmin_client.get(get_url(1) + "?public=false")
    assert response.status_code == 200
    assert len(response.json()["courses"]) == 1
    assert response.json()["courses"][0]["title"] == course.title
    assert response.json()["courses"][0]["is_public"] is False


def test_update_course_success(superadmin_client):
    # First, create a course to update
    create_payload = valid_create_course_payload()
    create_response = superadmin_client.post(get_url(1), json.dumps(create_payload), content_type="application/json")
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]
    _add_course_content(course_id)

    # Now, update the created course
    update_payload = valid_update_course_payload()
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")
    assert update_response.status_code == 200
    assert update_response.json()["id"] == course_id
    assert update_response.json()["title"] == update_payload["title"]
    assert update_response.json()["description"] == update_payload["description"]
    assert update_response.json()["enabled"] == update_payload["enabled"]


def test_update_course_with_target_audience_and_external_references(superadmin_client):
    # First, create a course to update
    create_payload = valid_create_course_payload()
    create_response = superadmin_client.post(get_url(1), json.dumps(create_payload), content_type="application/json")
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]
    _add_course_content(course_id)

    # Now, update the created course with target audience and external references
    update_payload = valid_update_course_payload()
    update_payload["target_audience"] = "Beginners with no prior programming experience."
    update_payload["external_references"] = [
        {
            "name": "GitHub Repository",
            "url": "https://github.com/AvaCodeSolutions/django-email-learning",
        },
        {
            "name": "Documentation",
            "url": "https://django-email-learning.readthedocs.io/",
        },
    ]
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")
    assert update_response.status_code == 200
    assert update_response.json()["id"] == course_id
    assert update_response.json()["target_audience"] == update_payload["target_audience"]
    assert update_response.json()["external_references"] == update_payload["external_references"]


def test_update_course_replaces_external_references(superadmin_client):
    create_payload = valid_create_course_payload()
    create_payload["external_references"] = [
        {"name": "Old Docs", "url": "https://example.com/old-docs"},
        {"name": "Old Repo", "url": "https://example.com/old-repo"},
    ]
    create_response = superadmin_client.post(get_url(1), json.dumps(create_payload), content_type="application/json")
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]
    _add_course_content(course_id)

    update_payload = valid_update_course_payload()
    update_payload["external_references"] = [{"name": "Updated Docs", "url": "https://example.com/new-docs"}]
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")

    assert update_response.status_code == 200
    assert update_response.json()["external_references"] == update_payload["external_references"]


def test_slug_change_not_allowed(superadmin_client):
    # First, create a course to update
    create_payload = valid_create_course_payload()
    create_response = superadmin_client.post(get_url(1), json.dumps(create_payload), content_type="application/json")
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    # Now, update the created course
    update_payload = valid_update_course_payload(title="New Title", description="New Description")
    update_payload["slug"] = "new-slug"  # Attempt to change slug
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")
    assert update_response.status_code == 400
    assert "error" in update_response.json()


def test_update_course_not_found(superadmin_client):
    update_payload = valid_update_course_payload()
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": 9999},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")
    assert update_response.status_code == 409
    assert "error" in update_response.json()


@pytest.fixture
def sample_course(superadmin_client):
    create_payload = valid_create_course_payload()
    create_response = superadmin_client.post(get_url(1), json.dumps(create_payload), content_type="application/json")
    assert create_response.status_code == 201
    return create_response.json()


def test_update_course_reset_imap_connection_conflict(sample_course, superadmin_client):
    course_id = sample_course["id"]
    update_payload = valid_update_course_payload(imap_connection_id=1, reset_imap_connection=True)
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")
    assert update_response.status_code == 409
    assert "error" in update_response.json()
    assert update_response.json()["error"] == "Cannot set imap_connection_id when reset_imap_connection is True."


def test_enabling_course_without_content_fails(sample_course, superadmin_client):
    course_id = sample_course["id"]
    update_payload = valid_update_course_payload(enabled=True)
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")
    assert update_response.status_code == 409
    assert update_response.json()["error"] == "Cannot enable a course that has no content."
    assert Course.objects.get(id=course_id).enabled is False


def test_enabling_course_with_content_succeeds(sample_course, superadmin_client):
    course_id = sample_course["id"]
    _add_course_content(course_id)
    update_payload = valid_update_course_payload(enabled=True)
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is True


def test_disabling_course_without_content_succeeds(sample_course, superadmin_client):
    course_id = sample_course["id"]
    update_payload = valid_update_course_payload(enabled=False)
    update_url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(update_url, json.dumps(update_payload), content_type="application/json")
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is False


def test_viewer_not_allowed_to_delete_course(sample_course, viewer_client):
    url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": sample_course["id"]},
    )
    delete_response = viewer_client.delete(url)
    assert delete_response.status_code == 403


@pytest.mark.parametrize("client", ["editor", "instructor"], indirect=["client"])
def test_editor_can_delete_course(sample_course, client):
    # Check that we have one course before the delete
    courses = client.get(get_url(1))
    assert len(courses.json().get("courses")) == 1

    url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": sample_course["id"]},
    )
    delete_response = client.delete(url)
    assert delete_response.status_code == 200

    # Check that we don't have any course after the delete
    courses = client.get(get_url(1))
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
        "language": "en",
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


def _add_course_content(course_id: int) -> CourseContent:
    lesson = Lesson.objects.create(title="Lesson", content="Content")
    return CourseContent.objects.create(
        course_id=course_id,
        priority=1,
        type=CourseContentType.LESSON,
        lesson=lesson,
        waiting_period=0,
    )


# ---------------------------------------------------------------------------
# Helper: get the OrganizationUser id for a given role (relies on users fixture)
# ---------------------------------------------------------------------------


def _org_user_id(role: str) -> int:
    return OrganizationUser.objects.filter(organization_id=1, role=role).first().id


# ---------------------------------------------------------------------------
# Instructor — create
# ---------------------------------------------------------------------------


def test_create_course_with_instructor_succeeds(users, superadmin_client):
    instructor_org_user_id = _org_user_id("instructor")
    payload = valid_create_course_payload()
    payload["instructors"] = [instructor_org_user_id]

    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")

    assert response.status_code == 201
    data = response.json()
    assert "instructors" in data
    assert len(data["instructors"]) == 1
    assert data["instructors"][0]["display_name"] == "Instructor Name"
    assert data["instructors"][0]["photo"] is None


def test_create_course_response_has_empty_instructors_list_when_none_assigned(users, superadmin_client):
    payload = valid_create_course_payload()
    # No instructors key in payload

    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")

    assert response.status_code == 201
    data = response.json()
    assert "instructors" in data
    # Serializer returns [] when no instructors exist (from_django_model always populates the list)
    assert data["instructors"] == [] or data["instructors"] is None


def test_create_course_with_non_instructor_org_user_fails(users, superadmin_client):
    editor_org_user_id = _org_user_id("editor")
    payload = valid_create_course_payload(slug=uuid.uuid4().hex)
    payload["instructors"] = [editor_org_user_id]

    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")

    assert response.status_code == 409
    assert "error" in response.json()
    assert "instructor role" in response.json()["error"]


def test_create_course_with_nonexistent_org_user_fails(users, superadmin_client):
    payload = valid_create_course_payload(slug=uuid.uuid4().hex)
    payload["instructors"] = [99999]  # does not exist

    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")

    assert response.status_code == 409
    assert "error" in response.json()
    assert "does not exist" in response.json()["error"]


def test_create_course_with_multiple_instructors(users, superadmin_client):
    """Only org users with instructor role are valid; add a second instructor org user first."""
    from django.contrib.auth.models import User as DjangoUser

    second_instructor_user = DjangoUser.objects.create_user(
        username="instructor2", email="instructor2@example.com", password="pass"
    )
    second_org_user = OrganizationUser.objects.create(
        user=second_instructor_user,
        organization_id=1,
        role="instructor",
        display_name="Instructor 2",
    )
    instructor_org_user_id = _org_user_id("instructor")

    payload = valid_create_course_payload(slug=uuid.uuid4().hex)
    payload["instructors"] = [instructor_org_user_id, second_org_user.id]

    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")

    assert response.status_code == 201
    data = response.json()
    assert len(data["instructors"]) == 2
    returned_names = {i["display_name"] for i in data["instructors"]}
    assert "Instructor Name" in returned_names
    assert "Instructor 2" in returned_names


# ---------------------------------------------------------------------------
# Instructor — response check on GET single course
# ---------------------------------------------------------------------------


def test_get_single_course_response_includes_instructors(users, superadmin_client):
    instructor_org_user_id = _org_user_id("instructor")
    payload = valid_create_course_payload(slug=uuid.uuid4().hex)
    payload["instructors"] = [instructor_org_user_id]

    create_response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    get_url_single = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    get_response = superadmin_client.get(get_url_single)

    assert get_response.status_code == 200
    data = get_response.json()
    assert "instructors" in data
    assert len(data["instructors"]) == 1
    assert data["instructors"][0]["display_name"] == "Instructor Name"
    assert data["instructors"][0]["photo"] is None


# ---------------------------------------------------------------------------
# Instructor — update (add, replace, remove)
# ---------------------------------------------------------------------------


def _single_course_url(course_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )


def test_update_course_adds_instructor(users, superadmin_client):
    instructor_org_user_id = _org_user_id("instructor")

    # Create course without instructors
    create_response = superadmin_client.post(
        get_url(1),
        json.dumps(valid_create_course_payload(slug=uuid.uuid4().hex)),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    # Update to assign instructor
    update_response = superadmin_client.post(
        _single_course_url(course_id),
        json.dumps({"instructors": [instructor_org_user_id]}),
        content_type="application/json",
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert len(data["instructors"]) == 1
    assert data["instructors"][0]["display_name"] == "Instructor Name"
    assert data["instructors"][0]["photo"] is None


def test_update_course_removes_instructor_when_not_in_list(users, superadmin_client):
    from django.contrib.auth.models import User as DjangoUser

    # Create a second instructor org user
    second_user = DjangoUser.objects.create_user(
        username="instructor_remove", email="instr_remove@example.com", password="pass"
    )
    second_org_user = OrganizationUser.objects.create(
        user=second_user,
        organization_id=1,
        role="instructor",
        display_name="Instructor Remove",
    )
    instructor_org_user_id = _org_user_id("instructor")

    # Create course with both instructors
    payload = valid_create_course_payload(slug=uuid.uuid4().hex)
    payload["instructors"] = [instructor_org_user_id, second_org_user.id]
    create_response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]
    assert len(create_response.json()["instructors"]) == 2

    # Update: only keep the first instructor (remove second)
    update_response = superadmin_client.post(
        _single_course_url(course_id),
        json.dumps({"instructors": [instructor_org_user_id]}),
        content_type="application/json",
    )

    assert update_response.status_code == 200
    data = update_response.json()

    assert len(data["instructors"]) == 1
    assert data["instructors"][0]["display_name"] == "Instructor Name"
    assert data["instructors"][0]["photo"] is None
    # Confirm DB record is gone
    assert not CourseInstructor.objects.filter(course_id=course_id, org_user=second_org_user).exists()


def test_update_course_clears_all_instructors_with_empty_list(users, superadmin_client):
    instructor_org_user_id = _org_user_id("instructor")

    payload = valid_create_course_payload(slug=uuid.uuid4().hex)
    payload["instructors"] = [instructor_org_user_id]
    create_response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    # Pass empty list to clear all instructors
    update_response = superadmin_client.post(
        _single_course_url(course_id),
        json.dumps({"instructors": []}),
        content_type="application/json",
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["instructors"] == []
    assert not CourseInstructor.objects.filter(course_id=course_id).exists()


def test_update_course_omitting_instructors_does_not_change_them(users, superadmin_client):
    """Passing no 'instructors' key should leave existing instructors untouched."""
    instructor_org_user_id = _org_user_id("instructor")

    payload = valid_create_course_payload(slug=uuid.uuid4().hex)
    payload["instructors"] = [instructor_org_user_id]
    create_response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    # Update title only — no 'instructors' key
    update_response = superadmin_client.post(
        _single_course_url(course_id),
        json.dumps({"title": "New Title"}),
        content_type="application/json",
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["title"] == "New Title"
    assert len(data["instructors"]) == 1
    assert data["instructors"][0]["display_name"] == "Instructor Name"
    assert data["instructors"][0]["photo"] is None


def test_update_course_with_non_instructor_role_fails(users, superadmin_client):
    editor_org_user_id = _org_user_id("editor")

    create_response = superadmin_client.post(
        get_url(1),
        json.dumps(valid_create_course_payload(slug=uuid.uuid4().hex)),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    update_response = superadmin_client.post(
        _single_course_url(course_id),
        json.dumps({"instructors": [editor_org_user_id]}),
        content_type="application/json",
    )

    assert update_response.status_code == 409
    assert "error" in update_response.json()
    assert "instructor role" in update_response.json()["error"]


def test_update_course_with_nonexistent_instructor_org_user_fails(users, superadmin_client):
    create_response = superadmin_client.post(
        get_url(1),
        json.dumps(valid_create_course_payload(slug=uuid.uuid4().hex)),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    update_response = superadmin_client.post(
        _single_course_url(course_id),
        json.dumps({"instructors": [99999]}),
        content_type="application/json",
    )

    assert update_response.status_code == 409
    assert "error" in update_response.json()
    assert "does not exist" in update_response.json()["error"]


# ---------------------------------------------------------------------------
# send_certificate field
# ---------------------------------------------------------------------------


def test_create_course_send_certificate_defaults_to_true(superadmin_client):
    payload = valid_create_course_payload()
    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    assert response.json()["send_certificate"] is True


def test_create_course_send_certificate_can_be_set_to_false(superadmin_client):
    payload = valid_create_course_payload(title="No Cert Course", slug="no-cert")
    payload["send_certificate"] = False
    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    assert response.json()["send_certificate"] is False
    assert Course.objects.get(id=response.json()["id"]).send_certificate is False


# ---------------------------------------------------------------------------
# can_create_course hook
# ---------------------------------------------------------------------------


def test_can_create_course_hook_blocks_creation(superadmin_client):
    from unittest.mock import patch

    from django_email_learning.platform.api.views import CourseCreationMixin

    with patch.object(CourseCreationMixin, "can_create_course", return_value=False):
        payload = valid_create_course_payload(title="Blocked Course", slug="blocked")
        response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")

    assert response.status_code == 403
    assert "error" in response.json()


def test_can_create_course_hook_allows_creation_by_default(superadmin_client):
    payload = valid_create_course_payload(title="Allowed Course", slug="allowed")
    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response.status_code == 201


def test_create_course_response_includes_can_create_course_true_by_default(
    superadmin_client,
):
    payload = valid_create_course_payload(title="Hook Course", slug="hook-course")
    response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")
    assert response.status_code == 201
    assert "can_create_course" in response.json()
    assert response.json()["can_create_course"] is True


def test_create_course_response_can_create_course_reflects_hook(superadmin_client):
    from unittest.mock import patch

    from django_email_learning.platform.api.views import CourseCreationMixin

    # First call (guard) returns True, second call (response field) returns False
    with patch.object(CourseCreationMixin, "can_create_course", side_effect=[True, False]):
        payload = valid_create_course_payload(title="Last Course", slug="last-course")
        response = superadmin_client.post(get_url(1), json.dumps(payload), content_type="application/json")

    assert response.status_code == 201
    assert response.json()["can_create_course"] is False


def test_delete_course_response_includes_can_create_course(sample_course, superadmin_client):
    url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": sample_course["id"]},
    )
    response = superadmin_client.delete(url)
    assert response.status_code == 200
    assert "can_create_course" in response.json()
    assert response.json()["can_create_course"] is True


def test_delete_course_response_can_create_course_reflects_hook(sample_course, superadmin_client):
    from unittest.mock import patch

    from django_email_learning.platform.api.views import CourseCreationMixin

    url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": sample_course["id"]},
    )
    with patch.object(CourseCreationMixin, "can_create_course", return_value=False):
        response = superadmin_client.delete(url)

    assert response.status_code == 200
    assert response.json()["can_create_course"] is False


def test_update_course_send_certificate(superadmin_client):
    create_response = superadmin_client.post(
        get_url(1),
        json.dumps(valid_create_course_payload(title="Cert Course", slug="cert")),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    course_id = create_response.json()["id"]

    url = reverse(
        "django_email_learning:api_platform:courses_detail",
        kwargs={"organization_id": 1, "course_id": course_id},
    )
    update_response = superadmin_client.post(
        url,
        json.dumps({"send_certificate": False}),
        content_type="application/json",
    )
    assert update_response.status_code == 200
    assert update_response.json()["send_certificate"] is False
    assert Course.objects.get(id=course_id).send_certificate is False
