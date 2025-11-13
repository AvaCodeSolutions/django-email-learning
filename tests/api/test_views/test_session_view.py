from django.urls import reverse
from django_email_learning.models import Organization
import pytest


@pytest.fixture(autouse=True)
def second_organization(db):
    org = Organization(name="Second Org", description="The second organization")
    org.save()
    return org


def test_update_session_view_as_viewer(viewer_client):
    url = reverse("django_email_learning:api:update_session_view")
    response = viewer_client.post(
        url, {"active_organization_id": 1}, content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json().get("active_organization_id") == 1
