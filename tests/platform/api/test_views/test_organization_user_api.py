import pytest
from django.urls import reverse

URL = reverse(
    "django_email_learning:api_platform:organization_users_list",
    kwargs={"organization_id": 1},
)


def get_single_user_url(organization_id, user_id):
    return reverse(
        "django_email_learning:api_platform:organization_users_detail",
        kwargs={"organization_id": organization_id, "user_id": user_id},
    )


def test_create_organization_user_as_superadmin(superadmin_client, second_user):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "editor",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == second_user.id
    assert data["role"] == "editor"


def test_admin_can_create_organization_user(platform_admin_client, second_user):
    response = platform_admin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "viewer",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == second_user.id
    assert data["role"] == "viewer"


@pytest.mark.parametrize("client", ["viewer", "editor"], indirect=["client"])
def test_other_roles_cannot_create_organization_user(client, second_user):
    response = client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "viewer",
        },
        content_type="application/json",
    )
    assert response.status_code == 403


def test_anonymous_cannot_create_organization_user(anonymous_client, second_user):
    response = anonymous_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "viewer",
        },
        content_type="application/json",
    )
    assert response.status_code == 401


def test_create_organization_user_with_invalid_role(superadmin_client, second_user):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "invalid_role",
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_create_organization_user_with_missing_fields(superadmin_client):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": 1,
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "error" in response.json()


def create_organization_user_with_nonexistent_user(superadmin_client):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": 9999,
            "role": "editor",
        },
        content_type="application/json",
    )
    assert response.status_code == 409
    assert "error" in response.json()


def test_create_organization_user_in_nonexistent_organization(superadmin_client, second_user):
    url = reverse(
        "django_email_learning:api_platform:organization_users_list",
        kwargs={"organization_id": 9999},
    )
    response = superadmin_client.post(
        url,
        data={
            "user_id": second_user.id,
            "role": "editor",
        },
        content_type="application/json",
    )
    assert response.status_code == 404
    assert "error" in response.json()


def test_delete_organization_user(superadmin_client, second_user):
    # Create a new user and add them to the organization
    response = superadmin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "editor",
        },
        content_type="application/json",
    )
    assert response.status_code == 201

    # Get list of all users in the organization to find the ID of the newly added user
    response = superadmin_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert any(user["user_id"] == second_user.id for user in data["organization_users"])
    organization_user = next(user for user in data["organization_users"] if user["user_id"] == second_user.id)

    # Now delete the user from the organization
    delete_url = get_single_user_url(1, organization_user["id"])
    response = superadmin_client.delete(delete_url)
    assert response.status_code == 200

    # Verify the user is no longer in the organization
    response = superadmin_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert not any(user["user_id"] == second_user.id for user in data["organization_users"])


@pytest.mark.parametrize("client", ["viewer", "editor"], indirect=["client"])
def test_other_roles_cannot_delete_organization_user(superadmin_client, client):
    org_users = superadmin_client.get(URL).json()["organization_users"]

    delete_response = client.delete(get_single_user_url(1, org_users[0]["id"]))
    assert delete_response.status_code == 403


def test_create_organization_user_instructor_includes_display_name_and_photo(superadmin_client, second_user):
    response = superadmin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "instructor",
            "display_name": "Test Instructor",
            "photo": "org_user_photos/test-instructor.png",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == second_user.id
    assert data["role"] == "instructor"
    assert data["display_name"] == "Test Instructor"
    assert data["photo"] == "org_user_photos/test-instructor.png"


def test_update_organization_user_includes_display_name_and_photo(superadmin_client, second_user):
    create_response = superadmin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "viewer",
        },
        content_type="application/json",
    )
    assert create_response.status_code == 201

    update_response = superadmin_client.post(
        get_single_user_url(1, second_user.id),
        data={
            "role": "instructor",
            "display_name": "Updated Instructor",
            "photo": "org_user_photos/updated-instructor.png",
        },
        content_type="application/json",
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["user_id"] == second_user.id
    assert data["role"] == "instructor"
    assert data["display_name"] == "Updated Instructor"
    assert data["photo"] == "org_user_photos/updated-instructor.png"


def test_list_organization_users_response_includes_display_name_and_photo(superadmin_client, second_user):
    create_response = superadmin_client.post(
        URL,
        data={
            "user_id": second_user.id,
            "role": "instructor",
            "display_name": "List Instructor",
            "photo": "org_user_photos/list-instructor.png",
        },
        content_type="application/json",
    )
    assert create_response.status_code == 201

    list_response = superadmin_client.get(URL)
    assert list_response.status_code == 200
    users = list_response.json()["organization_users"]

    org_user = next((user for user in users if user["user_id"] == second_user.id), None)
    assert org_user is not None
    assert "display_name" in org_user
    assert "photo" in org_user
    assert org_user["display_name"] == "List Instructor"
    assert org_user["photo"] == "org_user_photos/list-instructor.png"
