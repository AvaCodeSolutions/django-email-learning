from django.urls import reverse

from django_email_learning.models import ApiKeyScope
from django_email_learning.platform.features import PlatformFeature

URL = reverse("django_email_learning:platform:organization_detail_view", kwargs={"organization_id": 1})


def test_organization_api_feature_is_available_by_default(org_admin_client):
    response = org_admin_client.get(URL)
    assert response.status_code == 200
    assert PlatformFeature.ORGANIZATION_API.value in response.context["appContext"]["availableFeatures"]


def test_api_key_scopes_are_passed_to_the_frontend(org_admin_client):
    """The form's scope choices come from the enum the API validates against,
    so they can't offer a scope a key may not carry."""
    response = org_admin_client.get(URL)
    scopes = response.context["appContext"]["apiKeyScopes"]

    assert [scope["value"] for scope in scopes] == list(ApiKeyScope.values)
    assert all(scope["label"] for scope in scopes)
