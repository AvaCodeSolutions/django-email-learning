from django.urls import reverse


def test_enrollment_statistics(course, enrollments_factory, superadmin_client):
    enrollments_factory(course=course, status="unverified", count=3)
    url = reverse(
        "django_email_learning:api_platform:enrollments_statistics_view",
        args=[course.organization.id, course.id],
    )

    response = superadmin_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert "statistics" in data
    assert isinstance(data["statistics"], list)
    assert len(data["statistics"]) == 8
    assert data["statistics"][0]["date"] is not None
    assert data["statistics"][7]["count"] == 3
