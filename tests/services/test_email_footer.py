"""The optional per-course organization footer on course-scoped HTML emails.

Driven by `Course.show_organization_footer`; rendered from the shared
`emails/_organization_footer.html` partial via
`EmailSenderService.organization_footer_context`.
"""

from django.core import mail

from django_email_learning.models import EnrollmentStatus, SocialLink
from django_email_learning.services.command_models.send_assignment_command import (
    SendAssignmentCommand,
)
from django_email_learning.services.command_models.send_lesson_command import (
    SendLessonCommand,
)


def _html_body(email):
    return next(content for content, mimetype in email.alternatives if mimetype == "text/html")


def _add_social_links(organization):
    SocialLink.objects.create(organization=organization, platform="website", url="https://acme.example")
    SocialLink.objects.create(organization=organization, platform="linkedin", url="https://linkedin.com/company/acme")


def test_footer_absent_when_disabled(db, course_lesson_content):
    _add_social_links(course_lesson_content.course.organization)

    SendLessonCommand(
        command_name="send_lesson", content_id=course_lesson_content.id, email="learner@example.com"
    ).execute()

    html = _html_body(mail.outbox[0])
    assert 'class="email-social-links"' not in html
    assert "https://linkedin.com/company/acme" not in html


def test_base_footer_credit_is_present_even_without_org_footer(db, course_lesson_content):
    SendLessonCommand(
        command_name="send_lesson", content_id=course_lesson_content.id, email="learner@example.com"
    ).execute()

    html = _html_body(mail.outbox[0])
    assert '<div class="footer">' in html
    assert "Powered by" in html and "Django Email Learning" in html


def test_footer_shows_name_and_social_links_when_enabled(db, course_lesson_content):
    course = course_lesson_content.course
    course.show_organization_footer = True
    course.save()
    _add_social_links(course.organization)

    SendLessonCommand(
        command_name="send_lesson", content_id=course_lesson_content.id, email="learner@example.com"
    ).execute()

    email = mail.outbox[0]
    html = _html_body(email)
    assert course.organization.name in html
    assert 'class="email-social-links"' in html
    # Plain text links, not icons (Gmail strips inline SVG).
    assert '<a href="https://acme.example" class="email-social-link' in html
    assert ">Website</a>" in html
    assert '<a href="https://linkedin.com/company/acme" class="email-social-link' in html
    assert ">LinkedIn</a>" in html
    assert "<svg" not in html
    # The plain-text alternative is intentionally left untouched.
    assert "https://acme.example" not in email.body
    assert "linkedin.com/company/acme" not in email.body


def test_footer_name_is_plain_text_not_a_link(db, course_lesson_content):
    course = course_lesson_content.course
    course.show_organization_footer = True
    course.save()

    SendLessonCommand(
        command_name="send_lesson", content_id=course_lesson_content.id, email="learner@example.com"
    ).execute()

    html = _html_body(mail.outbox[0])
    assert f'<p class="email-org-name" style="margin: 0 0 20px;">{course.organization.name}</p>' in html


def test_footer_applies_to_other_course_emails(db, course_assignment_content):
    course = course_assignment_content.course
    course.show_organization_footer = True
    course.save()
    _add_social_links(course.organization)

    SendAssignmentCommand(
        command_name="send_assignment",
        content_id=course_assignment_content.id,
        email="learner@example.com",
        link="https://site.example/assignment",
    ).execute()

    html = _html_body(mail.outbox[0])
    assert 'href="https://acme.example"' in html


def test_footer_applies_to_certificate_email(db, active_enrollment):
    course = active_enrollment.course
    course.show_organization_footer = True
    course.save()
    _add_social_links(course.organization)
    active_enrollment.status = EnrollmentStatus.COMPLETED
    active_enrollment.save()

    active_enrollment.send_certificate_form()

    html = _html_body(mail.outbox[0])
    assert 'class="email-social-links"' in html
    assert 'href="https://acme.example"' in html
