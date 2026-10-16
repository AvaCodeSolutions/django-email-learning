import pytest
from django.core import mail

from django_email_learning.models import EnrollmentConfirmation, Newsletter, NewsletterSubscriber
from django_email_learning.services import enrollment_emails
from django_email_learning.services.enrollment_emails import (
    default_welcome_email_body,
    fill_placeholders,
    send_enrollment_email,
    send_welcome_email,
)

BUTTON = (
    '<a href="https://shop.example.com/pay" data-email-button="" '
    'data-query-params="ref=enrollment_id&amp;email=email">Pay now</a>'
)


@pytest.fixture
def gated_course(course):
    course.enrollment_confirmation = EnrollmentConfirmation.GATE
    course.enrollment_gate_key = "payment"
    course.save()
    return course


def test_placeholders_are_filled_with_the_course_values(course):
    text = fill_placeholders("{{ course_title }} by {{organization_name}}", course)

    assert text == f"{course.title} by {course.organization.name}"


def test_placeholders_are_escaped_in_html(course):
    course.title = "Tom & Jerry"
    course.save()

    assert fill_placeholders("<p>{{ course_title }}</p>", course, html=True) == "<p>Tom &amp; Jerry</p>"


def test_unknown_placeholders_are_left_alone(course):
    assert fill_placeholders("{{ learner_name }}", course) == "{{ learner_name }}"


def test_the_default_welcome_email_keeps_the_built_in_text(course):
    body = default_welcome_email_body(course)

    assert "{{ course_title }}" in body
    assert "{{ organization_name }}" in body
    assert "Welcome aboard!" in body


def test_a_course_without_its_own_welcome_email_sends_the_default(enrollment):
    send_welcome_email(enrollment)

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.subject == "Enrollment Verified"
    assert "has been successfully verified and confirmed" in sent.body
    assert enrollment.course.title in sent.body
    assert "{{" not in sent.body
    html = sent.alternatives[0][0]
    assert f"<strong>{enrollment.course.title}</strong>" in html


def test_the_welcome_email_is_sent_as_the_author_wrote_it(enrollment):
    course = enrollment.course
    course.welcome_email_subject = "Welcome to {{ course_title }}"
    course.welcome_email_body = f"<p>Hi from {{{{ organization_name }}}}</p>{BUTTON}"
    course.save()

    send_welcome_email(enrollment)

    sent = mail.outbox[0]
    assert sent.subject == f"Welcome to {course.title}"
    assert f"Hi from {course.organization.name}" in sent.body
    # The button carries the learner's own values, in both halves of the email.
    assert f"ref={enrollment.id}" in sent.body
    assert "email=user%40example.com" in sent.body
    assert f"ref={enrollment.id}" in sent.alternatives[0][0]


def test_the_welcome_email_still_offers_to_unsubscribe_from_the_linked_newsletter(enrollment):
    course = enrollment.course
    course.newsletter = Newsletter.objects.create(title="Weekly", organization_id=course.organization_id)
    course.welcome_email_body = "<p>Hi</p>"
    course.save()
    NewsletterSubscriber.objects.create(newsletter=course.newsletter, email=enrollment.learner.email)

    send_welcome_email(enrollment)

    assert "Weekly" in mail.outbox[0].body


def test_the_enrollment_email_has_no_verification_link(gated_course, enrollment):
    gated_course.enrollment_email_body = f"<p>Complete {{{{ course_title }}}}</p>{BUTTON}"
    gated_course.save()

    assert send_enrollment_email(enrollment) is True

    sent = mail.outbox[0]
    assert sent.subject == f"Complete your enrollment in {gated_course.title}"
    assert f"Complete {gated_course.title}" in sent.body
    assert f"https://shop.example.com/pay?ref={enrollment.id}" in sent.body
    assert "verify" not in sent.body.lower()


def test_an_empty_enrollment_email_sends_nothing(gated_course, enrollment):
    gated_course.enrollment_email_body = "<p></p>"
    gated_course.save()

    assert send_enrollment_email(enrollment) is False
    assert mail.outbox == []


def test_the_effective_text_falls_back_to_the_defaults(course):
    assert enrollment_emails.welcome_email_subject(course) == "Enrollment Verified"
    course.welcome_email_subject = ""
    assert enrollment_emails.welcome_email_subject(course) == "Enrollment Verified"
    course.welcome_email_body = ""
    # An emptied body is the author's choice, not a request for the default.
    assert enrollment_emails.welcome_email_body(course) == ""
