import pytest
from django.urls import reverse

URL = reverse("django_email_learning:platform:learners_view")


@pytest.mark.parametrize("client", ["org_admin", "instructor"], indirect=["client"])
def test_learners_accesible_to_org_admin_and_instructor(client):
    response = client.get(URL)
    assert response.status_code == 200


def test_learners_view_redirects_anonymous(anonymous_client):
    response = anonymous_client.get(URL)
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")
