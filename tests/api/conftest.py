from django.contrib.auth.models import User
from django_email_learning.models import OrganizationUser
from django.test import Client
import pytest


@pytest.fixture()
def users(db):
    superadmin = User(
        id=1,
        username="superadmin",
        email="admin@example.com",
        password="adminpass",
        is_superuser=True,
    )
    editor_user = User(
        id=2, username="editor", email="editor@example.com", password="editorpass"
    )
    platform_admin = User(
        id=3,
        username="platformadmin",
        email="platformadmin@example.com",
        password="platformadminpass",
    )
    viewer_user = User(
        id=4, username="viewer", email="viewer@example.com", password="viewerpass"
    )
    User.objects.bulk_create([superadmin, editor_user, platform_admin, viewer_user])
    editor = OrganizationUser(user=editor_user, organization_id=1, role="editor")
    admin = OrganizationUser(user=platform_admin, organization_id=1, role="admin")
    viewer = OrganizationUser(user=viewer_user, organization_id=1, role="viewer")
    OrganizationUser.objects.bulk_create([editor, admin, viewer])
    return {
        "superadmin": superadmin,
        "editor_user": editor_user,
        "platform_admin": platform_admin,
        "viewer_user": viewer_user,
    }


@pytest.fixture(scope="session")
def anonymous_client():
    return Client()


@pytest.fixture()
def superadmin_client(users):
    client = Client()
    client.force_login(users["superadmin"])
    return client


@pytest.fixture()
def editor_client(users):
    client = Client()
    client.force_login(users["editor_user"])
    return client


@pytest.fixture()
def platform_admin_client(users):
    client = Client()
    client.force_login(users["platform_admin"])
    return client


@pytest.fixture()
def viewer_client(users):
    client = Client()
    client.force_login(users["viewer_user"])
    return client


@pytest.fixture()
def client(
    request,
    superadmin_client,
    editor_client,
    platform_admin_client,
    viewer_client,
    anonymous_client,
):
    def _get_client(role_name):
        role_map = {
            "anonymous": anonymous_client,
            "superadmin": superadmin_client,
            "editor": editor_client,
            "platform_admin": platform_admin_client,
            "viewer": viewer_client,
        }
        return role_map.get(role_name)

    return _get_client(request.param)
