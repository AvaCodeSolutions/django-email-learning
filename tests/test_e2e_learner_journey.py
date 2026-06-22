"""
End-to-end learner journey tests.

These tests exercise the full pipeline through the real command/job classes
(EnrollCommand -> VerifyEnrollmentCommand -> DeliverContentsJob -> quiz
submission -> graduation -> certificate email) rather than testing each
component in isolation. The goal is to catch integration bugs that only
show up when steps are chained together in the order a real learner would
trigger them.

Written as part of a pre-1.0.0 QA pass.
"""

from django.core import mail
from django.test import TransactionTestCase
from django.urls import reverse

from django_email_learning.jobs.deliver_contents_job import DeliverContentsJob
from django_email_learning.models import (
    Answer,
    Assignment,
    Course,
    CourseContent,
    Enrollment,
    EnrollmentStatus,
    Learner,
    Lesson,
    Organization,
    Question,
    Quiz,
)
from django_email_learning.services import jwt_service
from django_email_learning.services.command_models.enroll_command import (
    EnrollCommand,
)
from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)


class FullLearnerJourneyTest(TransactionTestCase):
    """Lesson -> quiz -> graduation -> certificate, driven end to end."""

    def setUp(self) -> None:
        organization = Organization.objects.first()
        self.course = Course.objects.create(
            title="End to end course",
            slug="e2e-course",
            organization=organization,
            enabled=True,
            send_certificate=True,
        )
        self.lesson_content = CourseContent.objects.create(
            course=self.course,
            priority=1,
            type="lesson",
            lesson=Lesson.objects.create(title="Intro", content="Welcome!"),
            waiting_period=0,
            is_published=True,
        )
        quiz = Quiz.objects.create(
            title="Final quiz",
            required_score=50,
            selection_strategy="all",
            deadline_days=0,
            limited_attempts=False,
            is_blocking=True,
        )
        question = Question.objects.create(quiz=quiz, text="2 + 2?", priority=1)
        Answer.objects.create(question=question, text="4", is_correct=True)
        Answer.objects.create(question=question, text="5", is_correct=False)
        self.quiz_content = CourseContent.objects.create(
            course=self.course,
            priority=2,
            type="quiz",
            quiz=quiz,
            waiting_period=0,
            is_published=True,
        )
        self.quiz = quiz
        self.question = question

    def test_full_journey_lesson_then_quiz_completes_course(self) -> None:
        # 1. Enroll
        EnrollCommand(
            email="learner@example.com",
            course_slug=self.course.slug,
            organization_id=self.course.organization_id,
        ).execute()

        learner = Learner.objects.get(email="learner@example.com")
        enrollment = Enrollment.objects.get(learner=learner, course=self.course)
        self.assertEqual(enrollment.status, EnrollmentStatus.UNVERIFIED)
        self.assertIsNotNone(enrollment.activation_code)

        # 2. Verify
        VerifyEnrollmentCommand(
            enrollment_id=enrollment.id,
            verification_code=enrollment.activation_code,
        ).execute()
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, EnrollmentStatus.ACTIVE)
        self.assertTrue(enrollment.content_deliveries.exists())

        # 3. Run the delivery job - should send the lesson and schedule the quiz
        DeliverContentsJob().run()

        lesson_delivery = enrollment.content_deliveries.get(
            course_content=self.lesson_content
        )
        self.assertEqual(lesson_delivery.times_delivered, 1)
        self.assertTrue(
            enrollment.content_deliveries.filter(
                course_content=self.quiz_content
            ).exists()
        )

        # 4. Run the job again - should send the quiz
        DeliverContentsJob().run()
        quiz_delivery = enrollment.content_deliveries.get(
            course_content=self.quiz_content
        )
        self.assertEqual(quiz_delivery.times_delivered, 1)
        self.assertIsNotNone(quiz_delivery.link)

        # 5. Submit the quiz with a passing answer via the real public endpoint
        token = quiz_delivery.link.split("token=")[-1]
        decoded = jwt_service.decode_jwt(token)
        question_ids = decoded.get("question_ids") or [self.question.id]

        # NOTE: using TransactionTestCase (not TestCase), so on_commit callbacks
        # fire for real here - no need for captureOnCommitCallbacks, which is
        # only available on TestCase.
        response = self.client.post(
            reverse("django_email_learning:api_personalised:quiz_submission"),
            data={
                "token": token,
                "answers": [
                    {
                        "id": self.question.id,
                        "answers": [
                            a.id for a in self.question.answers.filter(is_correct=True)
                        ],
                    }
                    for qid in question_ids
                    if qid == self.question.id
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["passed"])

        # 6. Enrollment should have graduated automatically (no more content)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, EnrollmentStatus.COMPLETED)
        self.assertIsNotNone(enrollment.final_state_at)

        # 7. Certificate form email should have been sent via the on_commit hook
        certificate_emails = [
            m for m in mail.outbox if "certificate" in m.subject.lower()
        ]
        self.assertEqual(
            len(certificate_emails),
            1,
            "Expected exactly one certificate form email after graduation",
        )
        self.assertIn("learner@example.com", certificate_emails[0].to)


class NonBlockingAssignmentAsLastContentTest(TransactionTestCase):
    """
    Reproduces a gap found while building the end-to-end test above:
    DeliverContentsJob.process_delivery() graduates the enrollment when a
    LESSON is the last published content (explicit `else: ... graduate()`
    branch), but has no equivalent branch for a non-blocking ASSIGNMENT.

    If a course's last piece of content is a non-blocking assignment, the
    enrollment never reaches COMPLETED and the certificate is never sent.
    """

    def setUp(self) -> None:
        organization = Organization.objects.first()
        self.course = Course.objects.create(
            title="Assignment-ending course",
            slug="assignment-ending-course",
            organization=organization,
            enabled=True,
            send_certificate=False,
        )
        self.assignment_content = CourseContent.objects.create(
            course=self.course,
            priority=1,
            type="assignment",
            assignment=Assignment.objects.create(
                title="Final reflection",
                description="Write a short reflection.",
                is_blocking=False,
                deadline_days=0,
                requires_text_submission=True,
                requires_file_submission=False,
            ),
            waiting_period=0,
            is_published=True,
        )

    def test_non_blocking_assignment_as_last_content_should_graduate_but_does_not(
        self,
    ) -> None:
        EnrollCommand(
            email="learner2@example.com",
            course_slug=self.course.slug,
            organization_id=self.course.organization_id,
        ).execute()
        learner = Learner.objects.get(email="learner2@example.com")
        enrollment = Enrollment.objects.get(learner=learner, course=self.course)

        VerifyEnrollmentCommand(
            enrollment_id=enrollment.id,
            verification_code=enrollment.activation_code,
        ).execute()
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, EnrollmentStatus.ACTIVE)

        # Deliver the only (non-blocking) assignment - the last content in the course
        DeliverContentsJob().run()

        delivery = enrollment.content_deliveries.get(
            course_content=self.assignment_content
        )
        self.assertEqual(delivery.times_delivered, 1)

        enrollment.refresh_from_db()

        # This is the bug: the enrollment should be COMPLETED here, matching
        # the behaviour of a course that ends on a lesson, but it is not.
        # If this assertion starts failing, the upstream gap has been fixed
        # and this test (and its docstring) should be updated/removed.
        self.assertEqual(
            enrollment.status,
            EnrollmentStatus.ACTIVE,
            "If this fails, the non-blocking-assignment graduation gap in "
            "DeliverContentsJob.process_delivery() has been fixed upstream - "
            "update this test to assert COMPLETED instead.",
        )
