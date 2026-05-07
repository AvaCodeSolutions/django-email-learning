import pytest
from django.urls import reverse
from django.core.files.base import ContentFile
from django_email_learning.services import jwt_service
from django_email_learning.services.utils import PRIVATE_FILE_STORAGE
import datetime


URL = reverse("django_email_learning:platform:private_file_view")
ORG_ID = 1
TEST_FILE_PATH = "test_private_files/test_file.txt"
TEST_FILE_CONTENT = b"private file content"


@pytest.fixture(autouse=True)
def cleanup_test_file():
    yield
    if PRIVATE_FILE_STORAGE.exists(TEST_FILE_PATH):
        PRIVATE_FILE_STORAGE.delete(TEST_FILE_PATH)


@pytest.fixture()
def stored_file():
    PRIVATE_FILE_STORAGE.save(TEST_FILE_PATH, ContentFile(TEST_FILE_CONTENT))
    return TEST_FILE_PATH


def make_token(file_path=TEST_FILE_PATH, org_id=ORG_ID, expired=False):
    payload = {"file_path": file_path, "org_id": org_id}
    if expired:
        exp = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
        return jwt_service.generate_jwt(payload, exp=exp)
    return jwt_service.generate_jwt(payload)


# --- Authentication ---


def test_anonymous_user_redirects_to_login(anonymous_client):
    response = anonymous_client.get(URL)
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


# --- Token validation ---


def test_missing_token_returns_400(superadmin_client):
    response = superadmin_client.get(URL)
    assert response.status_code == 400


def test_invalid_token_returns_400(superadmin_client):
    response = superadmin_client.get(URL, {"token": "not.a.valid.token"})
    assert response.status_code == 400


def test_expired_token_returns_400(superadmin_client):
    token = make_token(expired=True)
    response = superadmin_client.get(URL, {"token": token})
    assert response.status_code == 400


def test_token_missing_file_path_returns_400(superadmin_client):
    token = jwt_service.generate_jwt({"org_id": ORG_ID})
    response = superadmin_client.get(URL, {"token": token})
    assert response.status_code == 400


def test_token_missing_org_id_returns_400(superadmin_client):
    token = jwt_service.generate_jwt({"file_path": TEST_FILE_PATH})
    response = superadmin_client.get(URL, {"token": token})
    assert response.status_code == 400


# --- Authorisation ---


@pytest.mark.parametrize("client", ["editor", "viewer"], indirect=["client"])
def test_editor_and_viewer_cannot_access_private_file(client, stored_file):
    token = make_token()
    response = client.get(URL, {"token": token})
    assert response.status_code == 404


@pytest.mark.parametrize(
    "client", ["superadmin", "org_admin", "instructor"], indirect=["client"]
)
def test_authorised_roles_can_access_private_file(client, stored_file):
    token = make_token()
    response = client.get(URL, {"token": token})
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == TEST_FILE_CONTENT


# --- File not found ---


def test_file_not_found_returns_404(superadmin_client):
    token = make_token(file_path="test_private_files/nonexistent.txt")
    response = superadmin_client.get(URL, {"token": token})
    assert response.status_code == 404


# --- Successful response ---


def test_successful_response_streams_file_content(superadmin_client, stored_file):
    token = make_token()
    response = superadmin_client.get(URL, {"token": token})
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == TEST_FILE_CONTENT
