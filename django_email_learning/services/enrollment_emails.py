"""The two emails a course sends around an enrollment's confirmation, as its author wrote them.

* The *enrollment email* goes out as a learner enrolls in a course whose enrollments are
  gated - in place of the verification email, since the learner has nothing to verify. It
  typically tells them what is pending and links to it, e.g. a payment page with a button
  carrying their enrollment id. Courses confirmed by email link keep the built-in
  verification email, so an author can never drop the link a learner needs.
* The *welcome email* goes out once the enrollment is confirmed, however that happened.
* The *enrollment reminder* goes out once to a gated enrollment still unconfirmed a while
  after enrolling, when the course turns it on. A course confirmed by email link sends a
  built-in verification reminder instead. See SendEnrollmentRemindersJob.

Both are rich text from the course editor and may hold buttons (see email_buttons). The
author can write `{{ course_title }}` and `{{ organization_name }}` anywhere in the subject
or body; they are filled in as each email is sent. A course that never edited one sends
the default below, so the text follows the course's language until it is customised.
"""

import logging
import re
from datetime import datetime
from html import escape
from typing import Optional

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.html import strip_tags
from django.utils.translation import gettext as _

from django_email_learning.models import Course, Enrollment, NewsletterSubscriber
from django_email_learning.services import jwt_service
from django_email_learning.services.email_buttons import link_variables, render_as_text, render_buttons
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.utils import mask_email

logger = logging.getLogger(__name__)

COURSE_TITLE = "course_title"
ORGANIZATION_NAME = "organization_name"
PLACEHOLDERS = (COURSE_TITLE, ORGANIZATION_NAME)

_PLACEHOLDER = re.compile(r"\{\{\s*(" + "|".join(PLACEHOLDERS) + r")\s*\}\}")


def _placeholder(name: str) -> str:
    return "{{ " + name + " }}"


def default_enrollment_email_subject(course: Course) -> str:
    with translation.override(course.language):
        return _("Complete your enrollment in %(course_title)s") % {COURSE_TITLE: _placeholder(COURSE_TITLE)}


def default_enrollment_email_body(course: Course) -> str:
    with translation.override(course.language):
        return "".join(
            [
                f"<p>{_('Hello there,')}</p>",
                "<p>"
                + _("Congratulations on enrolling in <strong>%(course_title)s</strong>!")
                % {COURSE_TITLE: _placeholder(COURSE_TITLE)}
                + " "
                + _("We're excited to have you join our learning community.")
                + "</p>",
                "<p>"
                + _("Your enrollment will start as soon as it is confirmed, and we will email you when it is.")
                + "</p>",
                f"<p>{_("If you didn't sign up for this course, you can safely ignore this email.")}</p>",
                f"<p>{_('Best regards,')}<br>{_placeholder(ORGANIZATION_NAME)}</p>",
            ]
        )


def default_welcome_email_subject(course: Course) -> str:
    with translation.override(course.language):
        return _("Enrollment Verified")


def default_welcome_email_body(course: Course) -> str:
    with translation.override(course.language):
        expectations = [
            _("Course materials will be delivered directly to this email address"),
            _("You'll receive structured lessons and assignments on a regular schedule"),
            _("Interactive content and assessments will help track your progress"),
        ]
        return "".join(
            [
                f"<p>{_('Hello there,')}</p>",
                "<p>"
                + _(
                    "Congratulations! Your enrollment for <strong>%(course_title)s</strong>"
                    " has been successfully verified and confirmed."
                )
                % {COURSE_TITLE: _placeholder(COURSE_TITLE)}
                + "</p>",
                f"<p>{_("We're excited to have you join our learning community. Here's what you can expect:")}</p>",
                "<ul>" + "".join(f"<li><p>{item}</p></li>" for item in expectations) + "</ul>",
                "<p>"
                + _(
                    "Your learning adventure begins soon!"
                    " Keep an eye on your inbox for the first lesson and welcome materials."
                )
                + "</p>",
                f"<h3>{_('Welcome aboard!')}</h3>",
                f"<p>{_('Best regards,')}<br>{_placeholder(ORGANIZATION_NAME)}</p>",
            ]
        )


def default_enrollment_reminder_subject(course: Course) -> str:
    with translation.override(course.language):
        return _("Your enrollment in %(course_title)s is still waiting") % {COURSE_TITLE: _placeholder(COURSE_TITLE)}


def default_enrollment_reminder_body(course: Course) -> str:
    with translation.override(course.language):
        return "".join(
            [
                f"<p>{_('Hello there,')}</p>",
                "<p>"
                + _("Your enrollment in <strong>%(course_title)s</strong> is still waiting to be confirmed.")
                % {COURSE_TITLE: _placeholder(COURSE_TITLE)}
                + " "
                + _("Complete the remaining step to start the course.")
                + "</p>",
                f"<p>{_("If you've already done it, you can ignore this email.")}</p>",
                f"<p>{_('Best regards,')}<br>{_placeholder(ORGANIZATION_NAME)}</p>",
            ]
        )


def enrollment_email_subject(course: Course) -> str:
    return course.enrollment_email_subject or default_enrollment_email_subject(course)


def enrollment_email_body(course: Course) -> str:
    return (
        course.enrollment_email_body
        if course.enrollment_email_body is not None
        else default_enrollment_email_body(course)
    )


def enrollment_reminder_subject(course: Course) -> str:
    return course.enrollment_reminder_subject or default_enrollment_reminder_subject(course)


def enrollment_reminder_body(course: Course) -> str:
    return (
        course.enrollment_reminder_body
        if course.enrollment_reminder_body is not None
        else default_enrollment_reminder_body(course)
    )


def welcome_email_subject(course: Course) -> str:
    return course.welcome_email_subject or default_welcome_email_subject(course)


def welcome_email_body(course: Course) -> str:
    return course.welcome_email_body if course.welcome_email_body is not None else default_welcome_email_body(course)


def has_content(html: str) -> bool:
    """Whether `html` says anything, rather than being empty markup left by an editor."""
    return bool(strip_tags(html).replace("&nbsp;", " ").strip()) or "<img" in html.lower()


def fill_placeholders(text: str, course: Course, html: bool = False) -> str:
    """`text` with each placeholder replaced by the course's value, escaped when `html`."""
    values = {COURSE_TITLE: course.title, ORGANIZATION_NAME: course.organization.name}
    return _PLACEHOLDER.sub(lambda match: escape(values[match.group(1)]) if html else values[match.group(1)], text)


_OPEN_TOKEN_SALT = "django_email_learning.enrollment_email_open"
# A separate salt, so a token from one email can never mark the other as opened.
_REMINDER_OPEN_TOKEN_SALT = "django_email_learning.enrollment_reminder_open"


def _site_base_url() -> str:
    return str(settings.DJANGO_EMAIL_LEARNING["SITE_BASE_URL"]).rstrip("/")


def enrollment_email_open_url(enrollment: Enrollment, reminder: bool = False) -> str:
    """The tracking pixel for the email a learner is sent as they enroll, or for its reminder.

    Signed rather than stored, and without an expiry: a learner may open the email weeks
    later, and the token can only ever mark this one enrollment's email as opened.
    """
    if reminder:
        token = signing.dumps(enrollment.id, salt=_REMINDER_OPEN_TOKEN_SALT)
        name = "track_enrollment_reminder_open"
    else:
        token = signing.dumps(enrollment.id, salt=_OPEN_TOKEN_SALT)
        name = "track_enrollment_email_open"
    return f"{_site_base_url()}{reverse(f'django_email_learning:personalised:{name}', kwargs={'token': token})}"


def enrollment_id_from_open_token(token: str, reminder: bool = False) -> Optional[int]:
    try:
        return int(signing.loads(token, salt=_REMINDER_OPEN_TOKEN_SALT if reminder else _OPEN_TOKEN_SALT))
    except (signing.BadSignature, TypeError, ValueError):
        return None


def verification_email_context(enrollment: Enrollment) -> dict:
    """Template context for the built-in verification email and its reminder, with a fresh link."""
    course = enrollment.course
    # The link never expires: a learner may open the email days later, and the default one
    # hour left them with a dead link. It can only ever activate this one enrollment, and
    # stops doing anything once the enrollment has been verified.
    token = jwt_service.generate_jwt(
        {
            "verification_code": enrollment.activation_code,
            "enrollment_id": enrollment.id,
        },
        exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()),
    )
    verification_path = reverse("django_email_learning:personalised:verify_enrollment") + f"?token={token}"
    return {
        "course_title": course.title,
        "verification_link": f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{verification_path}",
        "verification_code": enrollment.activation_code,
        "organization_name": course.organization.name,
        "support_imap_interface": course.imap_connection is not None,
        "imap_email_address": course.imap_connection.email if course.imap_connection else None,
        **email_sender_service.organization_footer_context(course),
    }


def _render(body: str, enrollment: Enrollment) -> tuple[str, str]:
    """`body` as the HTML and plain-text halves of an email to `enrollment`'s learner."""
    course = enrollment.course
    values = link_variables(enrollment_id=enrollment.id, email=enrollment.learner.email)
    html = render_buttons(fill_placeholders(body, course, html=True), values, course.organization.brand_color)
    text = fill_placeholders(render_as_text(body, values), course)
    return html, text


def send_enrollment_email(enrollment: Enrollment) -> bool:
    """Email a gated enrollment's learner the course's enrollment email; False when it is empty."""
    course = enrollment.course
    body = enrollment_email_body(course)
    if not has_content(body):
        logger.info(f"Course {course.id} has an empty enrollment email; nothing sent for {enrollment.id}.")
        return False
    message, message_text = _render(body, enrollment)
    context = {
        "message": message,
        "message_text": message_text,
        "track_open_url": enrollment_email_open_url(enrollment),
        **email_sender_service.organization_footer_context(course),
    }
    email = EmailMultiAlternatives(
        subject=fill_placeholders(enrollment_email_subject(course), course),
        body=render_to_string("emails/enrollment_gated.txt", context),
        from_email=email_sender_service.from_email_for_course(course),
        to=[enrollment.learner.email],
    )
    email.attach_alternative(render_to_string("emails/enrollment_gated.html", context), "text/html")
    email_sender_service.send(email)
    enrollment.enrollment_email_type = "enrollment"
    enrollment.save(update_fields=["enrollment_email_type"])
    logger.info(f"Enrollment email sent to {mask_email(enrollment.learner.email)} for enrollment {enrollment.id}")
    return True


def send_verification_reminder(enrollment: Enrollment) -> None:
    """Remind the learner of an unverified enrollment to verify it, with a fresh link."""
    course = enrollment.course
    context = {**verification_email_context(enrollment), "track_open_url": enrollment_email_open_url(enrollment, True)}
    email = EmailMultiAlternatives(
        subject=_("Reminder: verify your enrollment in %(course_title)s") % {COURSE_TITLE: course.title},
        body=render_to_string("emails/enrollment_verification_reminder.txt", context),
        from_email=email_sender_service.from_email_for_course(course),
        to=[enrollment.learner.email],
    )
    email.attach_alternative(render_to_string("emails/enrollment_verification_reminder.html", context), "text/html")
    email_sender_service.send(email)


def send_enrollment_reminder(enrollment: Enrollment) -> bool:
    """Remind the learner of a gated enrollment that it is still unconfirmed; False when the reminder is empty."""
    course = enrollment.course
    body = enrollment_reminder_body(course)
    if not has_content(body):
        return False
    message, message_text = _render(body, enrollment)
    context = {
        "message": message,
        "message_text": message_text,
        "track_open_url": enrollment_email_open_url(enrollment, reminder=True),
        **email_sender_service.organization_footer_context(course),
    }
    email = EmailMultiAlternatives(
        subject=fill_placeholders(enrollment_reminder_subject(course), course),
        body=render_to_string("emails/enrollment_gated.txt", context),
        from_email=email_sender_service.from_email_for_course(course),
        to=[enrollment.learner.email],
    )
    email.attach_alternative(render_to_string("emails/enrollment_gated.html", context), "text/html")
    email_sender_service.send(email)
    return True


def send_welcome_email(enrollment: Enrollment) -> None:
    """Email the learner of a newly confirmed enrollment the course's welcome email."""
    course = enrollment.course
    site_base_url = str(settings.DJANGO_EMAIL_LEARNING["SITE_BASE_URL"]).rstrip("/")
    course_image_url: Optional[str] = None
    if course.image:
        image_url = course.image.url
        course_image_url = image_url if image_url.startswith(("http://", "https://")) else site_base_url + image_url

    message, message_text = _render(welcome_email_body(course), enrollment)
    context = {
        "course_title": course.title,
        "message": message,
        "message_text": message_text,
        **email_sender_service.organization_footer_context(course),
    }
    newsletter_subscriber = (
        NewsletterSubscriber.objects.filter(newsletter=course.newsletter, email=enrollment.learner.email).first()
        if course.newsletter
        else None
    )
    if newsletter_subscriber:
        unsubscribe_path = reverse(
            "django_email_learning:public:newsletter_unsubscribe",
            kwargs={"token": newsletter_subscriber.unsubscribe_token},
        )
        context["newsletter_title"] = course.newsletter.title  # type: ignore[union-attr]
        context["newsletter_unsubscribe_url"] = f"{site_base_url}{unsubscribe_path}"

    email = EmailMultiAlternatives(
        subject=fill_placeholders(welcome_email_subject(course), course),
        body=render_to_string("emails/enrollment_verified.txt", context),
        from_email=email_sender_service.from_email_for_course(course),
        to=[enrollment.learner.email],
    )
    email.attach_alternative(
        render_to_string("emails/enrollment_verified.html", {**context, "course_image_url": course_image_url}),
        "text/html",
    )
    email_sender_service.send(email=email)
