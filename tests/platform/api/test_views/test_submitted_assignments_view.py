from django.urls import reverse
from django_email_learning.models import (
    AssignmentSubmission,
    ContentDelivery,
    Enrollment,
    Learner,
)
import pytest
import uuid


def get_url(organization_id: int, course_id: int) -> str:
    return reverse(
        "django_email_learning:api_platform:submitted_assignments_view",
        kwargs={"organization_id": organization_id, "course_id": course_id},
    )


@pytest.mark.parametrize(
    "client,expected_status",
    [
        ("org_admin", 200),
        ("instructor", 200),
        ("editor", 403),
        ("viewer", 403),
        ("anonymous", 401),
    ],
    indirect=["client"],
)
def test_submitted_assignments_view_get_role_access(
    client, expected_status, course_assignment_content, enrollment
):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    AssignmentSubmission.objects.create(
        delivery=delivery,
        text_submission="My answer",
    )

    response = client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
        )
    )

    assert response.status_code == expected_status


def test_submitted_assignments_view_returns_expected_list_fields(
    org_admin_client, course_assignment_content, enrollment
):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    submission = AssignmentSubmission.objects.create(
        delivery=delivery,
        text_submission="My answer",
    )

    response = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert payload["count"] == 1
    assert payload["page"] == 1
    assert payload["page_size"] == 50
    assert payload["has_more"] is False
    assert len(payload["items"]) == 1

    item = payload["items"][0]
    assert set(item.keys()) == {
        "id",
        "assignment_title",
        "submitted_at",
        "status",
        "reviewed_at",
        "reviewed_by",
    }
    assert item["id"] == submission.id
    assert item["assignment_title"] == course_assignment_content.assignment.title
    assert item["status"] == AssignmentSubmission.SubmissionStatus.PENDING_REVIEW
    assert item["reviewed_at"] is None
    assert item["reviewed_by"] is None


def test_submitted_assignments_view_filters_by_status(
    org_admin_client, course_assignment_content, enrollment
):
    delivery_approved = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    approved_submission = AssignmentSubmission.objects.create(
        delivery=delivery_approved,
        text_submission="Approved answer",
    )
    approved_submission.status = AssignmentSubmission.SubmissionStatus.APPROVED
    approved_submission.save()

    second_learner = Learner.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        organization_id=course_assignment_content.course.organization_id,
    )
    second_enrollment = Enrollment.objects.create(
        learner=second_learner,
        course=course_assignment_content.course,
    )
    delivery_pending = ContentDelivery.objects.create(
        enrollment=second_enrollment,
        course_content=course_assignment_content,
    )
    AssignmentSubmission.objects.create(
        delivery=delivery_pending,
        text_submission="Pending answer",
        status=AssignmentSubmission.SubmissionStatus.PENDING_REVIEW,
    )

    response_without_status = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
        )
    )
    assert response_without_status.status_code == 200
    assert len(response_without_status.json()["items"]) == 2

    response = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
        ),
        {"status": AssignmentSubmission.SubmissionStatus.APPROVED},
    )

    assert response.status_code == 200
    submissions = response.json()["items"]
    assert len(submissions) == 1
    assert submissions[0]["id"] == approved_submission.id
    assert submissions[0]["status"] == AssignmentSubmission.SubmissionStatus.APPROVED


def test_submitted_assignments_view_filters_by_learner_id(
    org_admin_client, course_assignment_content, enrollment
):
    delivery_first = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    first_submission = AssignmentSubmission.objects.create(
        delivery=delivery_first,
        text_submission="First learner answer",
    )

    second_learner = Learner.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        organization_id=course_assignment_content.course.organization_id,
    )
    second_enrollment = Enrollment.objects.create(
        learner=second_learner,
        course=course_assignment_content.course,
    )
    delivery_second = ContentDelivery.objects.create(
        enrollment=second_enrollment,
        course_content=course_assignment_content,
    )
    AssignmentSubmission.objects.create(
        delivery=delivery_second,
        text_submission="Second learner answer",
    )

    response_without_learner_id = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
        )
    )
    assert response_without_learner_id.status_code == 200
    assert len(response_without_learner_id.json()["items"]) == 2

    response = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
        ),
        {"learner_id": enrollment.learner.id},
    )

    assert response.status_code == 200
    submissions = response.json()["items"]
    assert len(submissions) == 1
    assert submissions[0]["id"] == first_submission.id


def test_submitted_assignments_view_pagination(
    org_admin_client, course_assignment_content, enrollment
):
    second_learner = Learner.objects.create(
        email=f"{uuid.uuid4().hex}@example.com",
        organization_id=course_assignment_content.course.organization_id,
    )
    second_enrollment = Enrollment.objects.create(
        learner=second_learner,
        course=course_assignment_content.course,
    )
    for enr in [enrollment, second_enrollment]:
        delivery = ContentDelivery.objects.create(
            enrollment=enr,
            course_content=course_assignment_content,
        )
        AssignmentSubmission.objects.create(
            delivery=delivery,
            text_submission="answer",
        )

    url = get_url(
        organization_id=course_assignment_content.course.organization_id,
        course_id=course_assignment_content.course_id,
    )

    page1 = org_admin_client.get(url, {"page": 1, "page_size": 1})
    assert page1.status_code == 200
    data1 = page1.json()
    assert data1["count"] == 2
    assert data1["page"] == 1
    assert data1["page_size"] == 1
    assert data1["has_more"] is True
    assert len(data1["items"]) == 1

    page2 = org_admin_client.get(url, {"page": 2, "page_size": 1})
    assert page2.status_code == 200
    data2 = page2.json()
    assert data2["count"] == 2
    assert data2["page"] == 2
    assert data2["has_more"] is False
    assert len(data2["items"]) == 1

    assert data1["items"][0]["id"] != data2["items"][0]["id"]


def test_submitted_assignments_view_default_pagination_fields_present(
    org_admin_client, course_assignment_content, enrollment
):
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    AssignmentSubmission.objects.create(
        delivery=delivery,
        text_submission="answer",
    )

    response = org_admin_client.get(
        get_url(
            organization_id=course_assignment_content.course.organization_id,
            course_id=course_assignment_content.course_id,
        )
    )

    assert response.status_code == 200
    payload = response.json()
    assert {"items", "count", "page", "page_size", "has_more"}.issubset(payload.keys())
