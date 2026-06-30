from django.urls import reverse


def test_organization_view_anonymous_client(db, anonymous_client):
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)
    assert response.status_code == 200
    assert response.context["appContext"]["organization"]["id"] == 1
    assert response.context["page_title"] == response.context["appContext"]["organization"]["name"]
    assert response.context["appContext"]["enrollApiUrl"].startswith("http")

    # No course added yet, so courses list should be empty
    assert len(response.context["appContext"]["organization"]["courses"]) == 0


def test_organization_view_anonymous_client_with_courses(db, anonymous_client, course):
    course.enabled = True
    course.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert len(response.context["appContext"]["organization"]["courses"]) == 1


def test_organization_view_non_existent_organization(db, anonymous_client):
    url = reverse(
        "django_email_learning:public:organization_view",
        kwargs={"organization_id": 999},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 404


def test_organization_view_excludes_disabled_courses(db, anonymous_client, course):
    course.enabled = False
    course.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert len(response.context["appContext"]["organization"]["courses"]) == 0


def test_organization_view_excludes_non_public_courses(db, anonymous_client, course):
    course.enabled = True
    course.is_public = False
    course.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert len(response.context["appContext"]["organization"]["courses"]) == 0


def test_organization_view_retuns_404_for_non_public_organization(db, anonymous_client, course):
    organization = course.organization
    organization.is_public = False
    organization.save()
    url = reverse("django_email_learning:public:organization_view", kwargs={"organization_id": 1})
    response = anonymous_client.get(url)

    assert response.status_code == 404
