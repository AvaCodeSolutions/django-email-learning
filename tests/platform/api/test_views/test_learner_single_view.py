from django.urls import reverse

from django_email_learning.models import Certificate, Learner, Organization


def test_single_llearner_viewe(viewer_client, enrollment):
    url = reverse(
        "django_email_learning:api_platform:learners_detail",
        kwargs={"organization_id": 1, "learner_id": enrollment.learner.id},
    )
    response = viewer_client.get(url)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == enrollment.learner.id
    assert data["email"] == enrollment.learner.email
    assert len(data["enrollments"]) == 1
    enrollment_data = data["enrollments"][0]
    assert enrollment_data["id"] == enrollment.id
    assert enrollment_data["progress"] == enrollment.progress_percentage()
    assert enrollment_data["course_title"] == enrollment.course.title
    assert enrollment_data["status"] == enrollment.status.value
    assert enrollment_data["certificate_url"] is None


def test_single_learner_view_contains_certificate_url_when_certificate_exists(viewer_client, enrollment):
    certificate = Certificate.objects.create(
        enrollment=enrollment,
        name_on_certificate="Jane Doe",
    )
    url = reverse(
        "django_email_learning:api_platform:learners_detail",
        kwargs={"organization_id": 1, "learner_id": enrollment.learner.id},
    )

    response = viewer_client.get(url)

    assert response.status_code == 200
    enrollment_data = response.json()["enrollments"][0]
    assert enrollment_data["certificate_url"] == "http://testserver" + reverse(
        "django_email_learning:personalised:certificate",
        kwargs={"certificate_number": certificate.certificate_number},
    )


def test_single_learner_view_cross_organization_returns_404(viewer_client):
    other_org = Organization.objects.create(pk=2, name="Other Organization")
    other_learner = Learner.objects.create(email="other-org-learner@example.com", organization=other_org)

    url = reverse(
        "django_email_learning:api_platform:learners_detail",
        kwargs={"organization_id": 1, "learner_id": other_learner.id},
    )
    response = viewer_client.get(url)
    assert response.status_code == 404


def test_single_learner_view_not_accessible_for_no_role(anonymous_client, enrollment):
    url = reverse(
        "django_email_learning:api_platform:learners_detail",
        kwargs={"organization_id": 1, "learner_id": enrollment.learner.id},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 401
