from django.urls import reverse

URL = reverse("django_email_learning:platform:learners_view")


def test_learners_accesible_to_org_admin(org_admin_client):
    response = org_admin_client.get(URL)
    assert response.status_code == 200


def test_learners_inaccessible_to_editor_and_viewer(editor_client, viewer_client):
    response = editor_client.get(URL)
    assert response.status_code == 403
    response = viewer_client.get(URL)
    assert response.status_code == 403
