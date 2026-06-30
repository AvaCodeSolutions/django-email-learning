import json

import pytest
from django.core.files.storage import default_storage
from django.test import override_settings
from django.urls import reverse


def get_url(organization_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:files_list",
        kwargs={"organization_id": organization_id},
    )


@pytest.fixture
def in_memory_storage():
    with override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}}):
        yield


def test_delete_uploaded_file_success(superadmin_client, in_memory_storage):
    file_path = "uploads/20260303/1/delete-me.png"
    with default_storage.open(file_path, "w") as file_handle:
        file_handle.write("dummy image")

    assert default_storage.exists(file_path)

    response = superadmin_client.delete(
        get_url(1),
        data=json.dumps({"file_path": file_path}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"message": "File deleted successfully"}
    assert not default_storage.exists(file_path)


def test_delete_uploaded_file_by_url_success(superadmin_client, in_memory_storage):
    file_path = "uploads/20260303/1/delete-by-url.png"
    with default_storage.open(file_path, "w") as file_handle:
        file_handle.write("dummy image")

    file_url = default_storage.url(file_path)
    response = superadmin_client.delete(
        get_url(1),
        data=json.dumps({"file_url": file_url}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"message": "File deleted successfully"}
    assert not default_storage.exists(file_path)


def test_delete_uploaded_file_invalid_path(superadmin_client):
    response = superadmin_client.delete(
        get_url(1),
        data=json.dumps({"file_path": "uploads/20260303/2/other-org.png"}),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid file path"}


def test_delete_uploaded_file_not_found(superadmin_client):
    response = superadmin_client.delete(
        get_url(1),
        data=json.dumps({"file_path": "uploads/20260303/1/missing.png"}),
        content_type="application/json",
    )

    assert response.status_code == 404
    assert response.json() == {"error": "File not found"}


@pytest.mark.parametrize("client", ["viewer", "anonymous"], indirect=True)
def test_delete_uploaded_file_requires_admin_or_editor(client):
    response = client.delete(
        get_url(1),
        data=json.dumps({"file_path": "uploads/20260303/1/blocked.png"}),
        content_type="application/json",
    )

    assert response.status_code in [401, 403]
