from django.urls import reverse


def test_single_llearner_viewe(viewer_client, enrollment):
    url = reverse(
        "django_email_learning:api_platform:single_learner_view",
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
    assert enrollment_data["course_title"] == enrollment.course.title
    assert enrollment_data["status"] == enrollment.status.value


def test_single_learner_view_not_accessible_for_no_role(anonymous_client, enrollment):
    url = reverse(
        "django_email_learning:api_platform:single_learner_view",
        kwargs={"organization_id": 1, "learner_id": enrollment.learner.id},
    )
    response = anonymous_client.get(url)
    assert response.status_code == 401
