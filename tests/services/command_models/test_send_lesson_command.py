from django.core import mail

from django_email_learning.models import (
    CourseContent,
    DecisionPoint,
    FromEmailType,
    GateUnlock,
    GateUnlockSource,
)
from django_email_learning.services.command_models.send_lesson_command import (
    SendLessonCommand,
)
from django_email_learning.services.email_sender_service import email_sender_service


def test_send_lesson_command(db, course_lesson_content):
    command = SendLessonCommand(
        command_name="send_lesson",
        content_id=course_lesson_content.id,
        email="test@example.com",
    )
    command.execute()

    assert len(mail.outbox) == 1
    email = mail.outbox[0]
    assert email.subject == course_lesson_content.lesson.title
    assert "test@example.com" in email.to
    assert course_lesson_content.lesson.content in email.body
    assert email.from_email == email_sender_service.from_email


def test_send_lesson_command_uses_organization_from_email(db, course_lesson_content, settings):
    settings.DJANGO_EMAIL_LEARNING = {
        **settings.DJANGO_EMAIL_LEARNING,
        "DOMAIN_WIDE_EMAIL": {"ENABLED": True, "DOMAIN": "learn.example.com"},
    }
    course = course_lesson_content.course
    course.from_email_type = FromEmailType.ORGANIZATION
    course.save()

    SendLessonCommand(
        command_name="send_lesson",
        content_id=course_lesson_content.id,
        email="test@example.com",
    ).execute()

    assert mail.outbox[0].from_email == email_sender_service.from_email_for_course(course)
    assert "@learn.example.com" in mail.outbox[0].from_email


def _coming_up_next(content: CourseContent, email: str = "user@example.com") -> str:
    mail.outbox.clear()
    SendLessonCommand(command_name="send_lesson", content_id=content.id, email=email).execute()
    html = mail.outbox[0].alternatives[0][0]
    return html.split("What’s coming up next?", 1)[1]


def test_coming_up_next_names_an_assignment(db, course_lesson_content, course_assignment_content):
    course_assignment_content.is_published = True
    course_assignment_content.save()

    assert "Sample Assignment assignment" in _coming_up_next(course_lesson_content)


def test_coming_up_next_names_a_decision(db, course, course_lesson_content):
    decision = DecisionPoint.objects.create(title="Pick your path", prompt="Which way?")
    CourseContent.objects.create(
        course=course, priority=2, type="decision", decision=decision, waiting_period=3600, is_published=True
    )

    assert "choose how the course continues: Pick your path" in _coming_up_next(course_lesson_content)


def test_coming_up_next_names_a_gate_the_learner_is_yet_to_pass(db, gate_course, active_enrollment):
    assert "waiting on: Payment" in _coming_up_next(gate_course.welcome)


def test_coming_up_next_looks_past_a_gate_the_learner_already_unlocked(db, gate_course, active_enrollment):
    GateUnlock.objects.create(
        enrollment=active_enrollment, course_content=gate_course.gate_content, source=GateUnlockSource.API
    )

    section = _coming_up_next(gate_course.welcome)
    assert "Payment" not in section
    assert "Paid lesson" in section
