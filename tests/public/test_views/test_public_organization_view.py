from django.urls import reverse


def test_organization_view_anonymous_client(db, anonymous_client):
    url = reverse(
        "django_email_learning:public:organization_view", kwargs={"organization_id": 1}
    )
    response = anonymous_client.get(url)
    assert response.status_code == 200
    assert response.context["organization"]["id"] == 1
    assert response.context["page_title"] == response.context["organization"]["name"]
    assert response.context["enroll_api_url"].startswith("http")
    assert "organization_json" in response.context

    # No course added yet, so courses list should be empty
    assert len(response.context["organization"]["courses"]) == 0


def test_organization_view_anonymous_client_with_courses(db, anonymous_client, course):
    course.enabled = True
    course.save()
    url = reverse(
        "django_email_learning:public:organization_view", kwargs={"organization_id": 1}
    )
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert len(response.context["organization"]["courses"]) == 1


def test_organization_view_non_existent_organization(db, anonymous_client):
    url = reverse(
        "django_email_learning:public:organization_view",
        kwargs={"organization_id": 999},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 404
