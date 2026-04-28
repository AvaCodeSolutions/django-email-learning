from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

import django_email_learning.jobs.deactivate_inactive_enrollments_job as deactivate_job_module
from django_email_learning.jobs.deactivate_inactive_enrollments_job import (
    DeactivateInactiveEnrollmentsJob,
)
from django_email_learning.models import (
    ContentDelivery,
    CourseContent,
    DeactivationReason,
    EnrollmentStatus,
    JobExecution,
    JobName,
    JobStatus,
    Lesson,
)


def test_deactivate_inactive_enrollments_job_exits_when_already_running(db):
    JobExecution.objects.create(
        job_name=JobName.DEACTIVATE_ENROLLMENTS.value,
        status=JobStatus.RUNNING.value,
    )

    with patch.object(
        deactivate_job_module.logger, "warning"
    ) as warning_spy, patch.object(
        deactivate_job_module.metric_service,
        "job_execution_started",
    ) as metric_started_spy, patch.object(
        deactivate_job_module.metric_service,
        "job_execution_finished",
    ) as metric_finished_spy:
        DeactivateInactiveEnrollmentsJob().run()

    assert (
        JobExecution.objects.filter(
            job_name=JobName.DEACTIVATE_ENROLLMENTS.value,
            status=JobStatus.RUNNING.value,
        ).count()
        == 1
    )
    warning_spy.assert_called_once()
    metric_started_spy.assert_not_called()
    metric_finished_spy.assert_not_called()


def test_deactivate_inactive_enrollments_job_deactivates_expired_quiz_delivery(
    db, enrollment, course_quiz_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    delivery.valid_until = timezone.now() - timedelta(days=1)
    delivery.save(update_fields=["valid_until"])

    with patch.object(
        DeactivateInactiveEnrollmentsJob,
        "send_deactivation_email",
    ) as send_email_spy, patch.object(
        deactivate_job_module.metric_service,
        "user_enrollment_deactivated",
    ) as user_metric_spy:
        DeactivateInactiveEnrollmentsJob().run()

    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.DEACTIVATED
    assert enrollment.deactivation_reason == DeactivationReason.INACTIVE

    send_email_spy.assert_called_once_with(
        enrollment.learner.email,
        course_quiz_content.quiz,
        course_quiz_content.course.title,
        course_quiz_content.course.organization.name,
    )
    user_metric_spy.assert_called_once_with(
        course_slug=course_quiz_content.course.slug,
        organization_id=course_quiz_content.course.organization.id,
        reason=DeactivationReason.INACTIVE.value,
    )

    job_execution = JobExecution.objects.get(
        job_name=JobName.DEACTIVATE_ENROLLMENTS.value,
    )
    assert job_execution.status == JobStatus.COMPLETED.value
    assert job_execution.finished_at is not None


def test_deactivate_inactive_enrollments_job_skips_non_quiz_deliveries(
    db, enrollment, course_lesson_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_lesson_content,
    )
    delivery.valid_until = timezone.now() - timedelta(days=1)
    delivery.save(update_fields=["valid_until"])

    with patch.object(
        DeactivateInactiveEnrollmentsJob,
        "send_deactivation_email",
    ) as send_email_spy, patch.object(
        deactivate_job_module.metric_service,
        "user_enrollment_deactivated",
    ) as user_metric_spy:
        DeactivateInactiveEnrollmentsJob().run()

    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.ACTIVE
    assert enrollment.deactivation_reason is None
    send_email_spy.assert_not_called()
    user_metric_spy.assert_not_called()


def test_deactivate_inactive_enrollments_job_does_not_deactivate_when_deadline_not_passed(
    db, enrollment, course_quiz_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    delivery.valid_until = timezone.now() + timedelta(days=1)
    delivery.save(update_fields=["valid_until"])

    with patch.object(
        DeactivateInactiveEnrollmentsJob,
        "send_deactivation_email",
    ) as send_email_spy, patch.object(
        deactivate_job_module.metric_service,
        "user_enrollment_deactivated",
    ) as user_metric_spy:
        DeactivateInactiveEnrollmentsJob().run()

    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.ACTIVE
    assert enrollment.deactivation_reason is None
    send_email_spy.assert_not_called()
    user_metric_spy.assert_not_called()


def test_deactivate_inactive_enrollments_job_non_blocking_quiz_should_not_deactivate_and_should_schedule_next_delivery(
    db, enrollment, course_quiz_content
):
    enrollment.status = EnrollmentStatus.ACTIVE
    enrollment.save()

    quiz = course_quiz_content.quiz
    quiz.is_blocking = False
    quiz.save(update_fields=["is_blocking"])

    next_lesson = Lesson.objects.create(
        title="Follow-up Lesson",
        content="Follow-up content",
    )

    next_content = CourseContent.objects.create(
        course=course_quiz_content.course,
        priority=course_quiz_content.priority + 1,
        type="lesson",
        lesson=next_lesson,
        waiting_period=3600,
        is_published=True,
    )

    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    delivery.valid_until = timezone.now() - timedelta(days=1)
    delivery.save(update_fields=["valid_until"])

    with patch.object(
        DeactivateInactiveEnrollmentsJob,
        "send_deactivation_email",
    ) as send_email_spy, patch.object(
        deactivate_job_module.metric_service,
        "user_enrollment_deactivated",
    ) as user_metric_spy:
        DeactivateInactiveEnrollmentsJob().run()

    enrollment.refresh_from_db()
    assert enrollment.status == EnrollmentStatus.ACTIVE
    assert enrollment.deactivation_reason is None
    assert ContentDelivery.objects.filter(
        enrollment=enrollment,
        course_content=next_content,
    ).exists()
    send_email_spy.assert_not_called()
    user_metric_spy.assert_not_called()


def test_deactivate_inactive_enrollments_job_triggers_started_metric(db):
    with patch.object(
        deactivate_job_module.metric_service,
        "job_execution_started",
    ) as metric_started_spy:
        DeactivateInactiveEnrollmentsJob().run()

    metric_started_spy.assert_called_once_with(job_name="deactivate_enrollments")


def test_deactivate_inactive_enrollments_job_triggers_finished_metric(db):
    with patch.object(
        deactivate_job_module.metric_service,
        "job_execution_finished",
    ) as metric_finished_spy:
        DeactivateInactiveEnrollmentsJob().run()

    metric_finished_spy.assert_called_once()
    call_kwargs = metric_finished_spy.call_args
    assert call_kwargs.kwargs["job_name"] == "deactivate_enrollments"
    assert isinstance(call_kwargs.kwargs["execution_time"], int)
