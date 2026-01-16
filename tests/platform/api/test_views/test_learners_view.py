from django.urls import reverse
from django_email_learning.models import Learner, Enrollment, EnrollmentStatus, Course
import pytest
import uuid


URL = reverse(
    "django_email_learning:api_platform:learners_view", kwargs={"organization_id": 1}
)


@pytest.fixture(scope="function")
def learners_factory(course):
    def _learners_factory(count: int):
        for i in range(count):
            uid = uuid.uuid4().hex
            learner = Learner.objects.create(
                email=f"{uid}@example.com", organization_id=1
            )
            Enrollment.objects.create(learner=learner, course=course)

    return _learners_factory


@pytest.mark.parametrize("page,has_more", [(1, True), (2, True), (3, False)])
def test_learners_view_pagination(page, has_more, superadmin_client, learners_factory):
    learners_factory(25)

    learners = Learner.objects.filter(organization_id=1)
    assert learners.count() == 25

    response = superadmin_client.get(f"{URL}?page={page}&page_size=10")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 25
    assert len(data["items"]) <= 10
    assert data["page"] == page
    assert data["page_size"] == 10
    assert data["has_more"] is has_more


def test_learner_view_accesible_for_platform_viewer(viewer_client, learners_factory):
    learners_factory(5)

    response = viewer_client.get(URL)

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert len(data["items"]) == 5


def test_learner_view_not_accesible_for_no_role(anonymous_client, learners_factory):
    learners_factory(5)

    response = anonymous_client.get(URL)

    assert response.status_code == 401


def test_learners_view_search(superadmin_client, learners_factory):
    learners_factory(10)
    # Create a specific learner to search for
    specific_learner = Learner.objects.create(
        email="specific_learner@example.com", organization_id=1
    )
    Enrollment.objects.create(learner=specific_learner, course_id=1)
    response = superadmin_client.get(f"{URL}?search=specific_learner")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["email"] == "specific_learner@example.com"


def test_learners_view_course_filter(superadmin_client, learners_factory, course):
    learners_factory(10)
    # Create a specific learner enrolled in a different course
    specific_learner = Learner.objects.create(
        email="specific_learner@example.com", organization_id=1
    )
    course = Course.objects.create(
        title="Another Course", organization_id=1, enabled=True
    )
    Enrollment.objects.create(learner=specific_learner, course_id=course.id)

    response = superadmin_client.get(f"{URL}?course_id=2")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["email"] == "specific_learner@example.com"


def test_learners_view_is_active_filter(superadmin_client, learners_factory, course):
    learners_factory(10)
    # Create a specific active learner
    active_learner = Learner.objects.create(
        email="active_learner@example.com", organization_id=1
    )
    Enrollment.objects.create(
        learner=active_learner, course_id=1, status=EnrollmentStatus.ACTIVE
    )

    response = superadmin_client.get(f"{URL}?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1

    response = superadmin_client.get(URL)
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 11
