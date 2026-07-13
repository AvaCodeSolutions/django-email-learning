from django.urls import reverse

from django_email_learning.models import Course, Organization


def test_enrollment_statistics_cross_organization_returns_empty(course, enrollments_factory, editor_client):
    other_org = Organization.objects.create(pk=2, name="Other Organization")
    other_course = Course.objects.create(
        title="Other Org Course",
        slug="other-org-course",
        description="Belongs to a different organization.",
        organization=other_org,
    )
    enrollments_factory(course=other_course, status="unverified", count=3)

    url = reverse(
        "django_email_learning:api_platform:enrollments_statistics",
        args=[course.organization.id, other_course.id],
    )

    response = editor_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert all(day["count"] == 0 for day in data["statistics"])


def test_enrollment_statistics(course, enrollments_factory, superadmin_client):
    enrollments_factory(course=course, status="unverified", count=3)
    url = reverse(
        "django_email_learning:api_platform:enrollments_statistics",
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
