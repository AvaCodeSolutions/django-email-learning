from django.urls import reverse
from django_email_learning.models import ImapConnection


def get_url(organization_id: int) -> str:
    return reverse(
        "django_email_learning:api:imap_connection_view",
        kwargs={"organization_id": organization_id},
    )


def test_get_imap_connections_unauthenticated(anonymous_client):
    response = anonymous_client.get(get_url(1))
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


def test_get_imap_connections_authenticated(superadmin_client):
    response = superadmin_client.get(get_url(1))
    assert response.status_code == 200
    assert "imap_connections" in response.json()
    assert isinstance(response.json()["imap_connections"], list)
    assert len(response.json()["imap_connections"]) == 0


def test_get_imap_connections_with_data(superadmin_client, viewer_client):
    ImapConnection.objects.create(
        organization_id=1,
        server="imap.example.com",
        port=993,
        email="user@example.com",
        password="password",
    )
    imap_response = viewer_client.get(get_url(1))
    assert imap_response.status_code == 200
    assert "imap_connections" in imap_response.json()
    assert isinstance(imap_response.json()["imap_connections"], list)
    assert len(imap_response.json()["imap_connections"]) == 1

    imap_connection = imap_response.json()["imap_connections"][0]
    assert imap_connection["server"] == "imap.example.com"
    assert imap_connection["port"] == 993
    assert imap_connection["email"] == "user@example.com"
    assert "password" not in imap_connection
    assert imap_connection["organization_id"] == 1
    assert "id" in imap_connection


def test_create_imap_connection_success(superadmin_client):
    payload = {
        "email": "user@example.com",
        "password": "aSafePassword123!",
        "server": "imap.example.com",
        "port": 993,
    }
    response = superadmin_client.post(
        get_url(1), data=payload, content_type="application/json"
    )
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["email"] == payload["email"]
    assert response.json()["server"] == payload["server"]
    assert response.json()["port"] == payload["port"]
    assert response.json()["organization_id"] == 1
