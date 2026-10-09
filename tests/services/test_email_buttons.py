"""Buttons in rich-text content: what is kept on save, and the links each learner gets."""

from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from django_email_learning.jobs.send_newsletters_job import SendNewslettersJob
from django_email_learning.models import (
    ContentDelivery,
    Newsletter,
    NewsletterSubscriber,
    Sendout,
    SendoutDelivery,
)
from django_email_learning.services.command_models.send_gate_command import SendGateCommand
from django_email_learning.services.command_models.send_lesson_command import SendLessonCommand
from django_email_learning.services.email_buttons import (
    button_url,
    link_variables,
    render_as_text,
    render_buttons,
)
from django_email_learning.services.sanitize import sanitize_rich_text

BUTTON = (
    '<p>Fish &amp; chips</p><a href="https://shop.example.com/pay?plan=pro" data-email-button="" '
    'data-query-params="client_reference_id=enrollment_id&amp;email=email">Pay &lt;now&gt;</a>'
)
VALUES = link_variables(enrollment_id=42, email="jane+x@example.com")
PERSONAL_URL = "https://shop.example.com/pay?plan=pro&client_reference_id=42&email=jane%2Bx%40example.com"


def test_the_sanitizer_keeps_a_button_and_strips_anything_else_on_it():
    cleaned = sanitize_rich_text(BUTTON.replace("<a ", '<a onclick="steal()" class="x" '))

    assert cleaned == BUTTON


def test_a_button_becomes_a_call_to_action_with_the_learners_values():
    html = render_buttons(BUTTON, VALUES, brand_color="#4a5ec0")

    assert html == (
        '<p>Fish &amp; chips</p><div class="email-cta-wrap" style="text-align: center;">'
        f'<a href="{PERSONAL_URL.replace("&", "&amp;")}" class="email-cta" target="_blank" '
        'rel="noopener noreferrer" '
        'style="background-color: #4a5ec0; border-color: #4a5ec0; color: #ffffff !important;">'
        "Pay &lt;now&gt;</a></div>"
    )


def test_a_button_keeps_the_alignment_it_was_given():
    aligned = BUTTON.replace("<a ", '<a style="text-align: right;" ')

    assert '<div class="email-cta-wrap" style="text-align: right;">' in render_buttons(
        sanitize_rich_text(aligned), VALUES
    )


def test_a_light_brand_colour_gets_dark_text():
    assert "color: #232936 !important" in render_buttons(BUTTON, VALUES, brand_color="#f5c518")


@pytest.mark.parametrize("brand_color", [None, "", "red", "#fff", "#12345g", "#123456; background: url(x)"])
def test_a_missing_or_malformed_brand_colour_falls_back_to_the_default(brand_color):
    assert "background-color: #636eec;" in render_buttons(BUTTON, VALUES, brand_color=brand_color)


def test_content_without_buttons_is_left_exactly_as_it_was():
    html = '<p>Fish &amp; chips &#169;</p><p><a href="https://a.example/?x=1&amp;y=2">plain</a><br></p>'

    assert render_buttons(html, VALUES) == html


def test_a_plain_link_next_to_a_button_is_untouched():
    html = BUTTON + '<p><a href="https://a.example/?x=1&amp;y=2">plain</a></p>'

    assert render_buttons(html, VALUES).endswith('<p><a href="https://a.example/?x=1&amp;y=2">plain</a></p>')


def test_a_value_that_is_missing_is_left_off():
    assert button_url("https://shop.example.com/pay", "ref=enrollment_id&e=email", link_variables(email="a@b.co")) == (
        "https://shop.example.com/pay?e=a%40b.co"
    )


@pytest.mark.parametrize(
    "query_params",
    ["ref=password", "ref=", "bad name=email", "=email"],
)
def test_unknown_variables_and_bad_names_are_ignored(query_params):
    assert button_url("https://shop.example.com/pay", query_params, VALUES) == "https://shop.example.com/pay"


def test_as_text_a_button_keeps_its_link():
    text = render_as_text(BUTTON + "<p>Bye</p>", VALUES)

    assert text == f"Fish & chips\n\nPay <now>: {PERSONAL_URL}\nBye"


def test_a_lesson_email_links_each_learner_with_their_enrollment(course_lesson_content, active_enrollment):
    course_lesson_content.lesson.content = BUTTON
    course_lesson_content.lesson.save()
    mail.outbox.clear()

    SendLessonCommand(content_id=course_lesson_content.id, email=active_enrollment.learner.email).execute()

    [message] = mail.outbox
    expected = button_url(
        "https://shop.example.com/pay?plan=pro",
        "client_reference_id=enrollment_id&email=email",
        link_variables(active_enrollment.id, active_enrollment.learner.email),
    )
    assert expected.replace("&", "&amp;") in message.alternatives[0][0]
    assert f"client_reference_id={active_enrollment.id}" in expected
    # The text alternative carries the link too, and is not HTML-escaped.
    assert expected in message.body
    assert "&amp;" not in message.body
    brand_color = course_lesson_content.course.organization.brand_color
    assert f"background-color: {brand_color};" in message.alternatives[0][0]


def test_a_lesson_sent_without_an_enrollment_leaves_the_enrollment_off(course_lesson_content):
    course_lesson_content.lesson.content = BUTTON
    course_lesson_content.lesson.save()
    mail.outbox.clear()

    SendLessonCommand(content_id=course_lesson_content.id, email="admin@example.com").execute()

    assert "https://shop.example.com/pay?plan=pro&email=admin%40example.com" in mail.outbox[0].body


def test_a_gate_email_links_with_the_enrollment(gate_course, active_enrollment):
    gate_course.gate.message = BUTTON
    gate_course.gate.save()
    ContentDelivery.objects.create(enrollment=active_enrollment, course_content=gate_course.gate_content)
    mail.outbox.clear()

    SendGateCommand(
        content_id=gate_course.gate_content.id,
        enrollment_id=active_enrollment.id,
        email=active_enrollment.learner.email,
    ).execute()

    assert f"client_reference_id={active_enrollment.id}" in mail.outbox[0].body


def test_a_newsletter_button_can_only_carry_the_email(db):
    newsletter = Newsletter.objects.create(title="Weekly", language="en", organization_id=1)
    sendout = Sendout.objects.create(
        newsletter=newsletter, subject="Hi", body=BUTTON, scheduled_at=timezone.now(), status=Sendout.Status.SCHEDULED
    )
    subscriber = NewsletterSubscriber.objects.create(newsletter=newsletter, email="sub@example.com")
    delivery = SendoutDelivery.objects.create(
        sendout=sendout, subscriber=subscriber, status=SendoutDelivery.Status.PROCESSING
    )

    with patch("django_email_learning.jobs.send_newsletters_job.email_sender_service.send") as send:
        SendNewslettersJob().process_delivery(delivery)

    message = send.call_args[0][0]
    assert "https://shop.example.com/pay?plan=pro&amp;email=sub%40example.com" in message.alternatives[0][0]
    assert message.body.startswith(
        "Fish & chips\n\nPay <now>: https://shop.example.com/pay?plan=pro&email=sub%40example.com"
    )
