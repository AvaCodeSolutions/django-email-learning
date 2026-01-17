from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.jobs.deliver_contents_job import SendLessonCommand
from django_email_learning.models import (
    DeliverySchedule,
    ContentDelivery,
    Course,
    CourseContent,
    EnrollmentStatus,
    Enrollment,
    DeliveryStatus,
)
from tests.jobs.delivery_queue_mock import DeliveryQueueMock
from unittest.mock import patch
import pytest


@pytest.fixture
def delivery_queue_mock():
    mock = DeliveryQueueMock()
    with patch(
        "django_email_learning.services.defaults.database_delivery_queue.DatabaseDeliveryQueue",
        return_value=mock,
    ):
        yield mock


def test_deliver_contents_job_runs_no_tasks(db, delivery_queue_mock):
    job = DeliverContentsJob()
    job.run()
    assert delivery_queue_mock.index == 0


def test_deliver_contents_job_runs_with_tasks(
    db, delivery_queue_mock, enrollment, course_lesson_content, course_quiz_content
):
    # Create mock DeliverySchedule objects
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    # Delivery for the first nrollment on the lesson content - only one content - should graduate after delivery
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment, course_content=course_lesson_content
    )

    delivery_schedule1 = DeliverySchedule.objects.create(delivery=delivery)
    # Delivery for the second enrollment on another course with next content available
    course2 = Course.objects.create(
        title="Test Course", slug="test-course", organization_id=1
    )
    enrollment2 = Enrollment.objects.create(
        learner=enrollment.learner, course=course2, status=EnrollmentStatus.ACTIVE
    )
    course_content_2 = CourseContent.objects.create(
        course=course2,
        priority=1,
        type="lesson",
        is_published=True,
        lesson=course_lesson_content.lesson,
        waiting_period=3600,
    )
    course_content_3 = CourseContent.objects.create(
        course=course2,
        priority=2,
        type="quiz",
        is_published=True,
        quiz=course_quiz_content.quiz,
        waiting_period=3600,
    )
    delivery2 = ContentDelivery.objects.create(
        enrollment=enrollment2, course_content=course_content_2
    )
    delivery_schedule2 = DeliverySchedule.objects.create(
        delivery=delivery2,
    )

    # Add tasks to the mock delivery queue
    delivery_queue_mock.add_task(delivery_schedule1)
    delivery_queue_mock.add_task(delivery_schedule2)

    # before the job run there is no content delivery for course_content_3
    assert not ContentDelivery.objects.filter(
        enrollment=enrollment2, course_content=course_content_3
    ).exists()

    # Before running the job, both delivery schedules should be in SCHEDULED status
    assert delivery_schedule1.status == DeliveryStatus.SCHEDULED
    assert delivery_schedule2.status == DeliveryStatus.SCHEDULED

    job = DeliverContentsJob()
    job.run()

    # After running the job, both delivery schedules should be in DELIVERED status
    delivery_schedule1.refresh_from_db()
    delivery_schedule2.refresh_from_db()
    assert delivery_schedule1.status == DeliveryStatus.DELIVERED
    assert delivery_schedule2.status == DeliveryStatus.DELIVERED

    assert delivery_queue_mock.index == 2

    # First enrollment should be completed after receiving the only content
    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.COMPLETED

    # Second enrollment should remain active after receiving the first content
    enrollment2.refresh_from_db()
    assert enrollment2.status == EnrollmentStatus.ACTIVE
    # A new ContentDelivery for the next content (quiz) should be created for the second enrollment
    assert ContentDelivery.objects.filter(
        enrollment=enrollment2, course_content=course_content_3
    ).exists()


def test_deliver_contents_job_blocks_after_3_failed_attempts(
    db, delivery_queue_mock, enrollment, course_lesson_content
):
    # Create mock DeliverySchedule object
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment, course_content=course_lesson_content
    )

    delivery_schedule = DeliverySchedule.objects.create(
        delivery=delivery, failed_attempts=3
    )

    # Add task to the mock delivery queue
    delivery_queue_mock.add_task(delivery_schedule)

    job = DeliverContentsJob()

    # Patch the send_lesson_content method to always raise an exception
    with patch.object(
        SendLessonCommand,
        "execute",
        side_effect=Exception("Simulated sending failure"),
    ):
        job.run()

    # After running the job, the delivery schedule should be in BLOCKED status
    delivery_schedule.refresh_from_db()
    assert delivery_schedule.status == DeliveryStatus.BLOCKED
    assert delivery_schedule.failed_attempts == 3


def test_deliver_contents_job_reschedules_failed_delivery_and_increments_attempts(
    db, delivery_queue_mock, enrollment, course_lesson_content
):
    # Create mock DeliverySchedule object
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment, course_content=course_lesson_content
    )

    delivery_schedule = DeliverySchedule.objects.create(
        delivery=delivery, failed_attempts=1
    )

    original_time = delivery_schedule.time

    # Add task to the mock delivery queue
    delivery_queue_mock.add_task(delivery_schedule)

    job = DeliverContentsJob()

    # Patch the send_lesson_content method to always raise an exception
    with patch.object(
        SendLessonCommand,
        "execute",
        side_effect=Exception("Simulated sending failure"),
    ):
        job.run()

    # After running the job, the delivery schedule should be rescheduled and attempts incremented
    delivery_schedule.refresh_from_db()
    assert delivery_schedule.status == DeliveryStatus.SCHEDULED
    assert delivery_schedule.failed_attempts == 2
    assert delivery_schedule.time > original_time
