"""Answering a decision point.

The first answer is the only one: it is recorded, retires the link, and sends the learner
wherever the rules on the decision point it - or on to the next content when none do.
"""

from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone

from django_email_learning.models import (
    ContentDelivery,
    ContentTrack,
    ContentTransition,
    CourseContent,
    DeactivationReason,
    DecisionOption,
    DecisionPoint,
    DecisionResponse,
    EnrollmentStatus,
    Lesson,
    TransitionCondition,
)
from django_email_learning.services import jwt_service
from django_email_learning.services.email_sender_service import email_sender_service

URL = reverse("django_email_learning:api_personalised:decision_submission")
AMP_URL = reverse("django_email_learning:api_personalised:decision_amp_submission")


def make_decision_content(course, priority=1):
    decision = DecisionPoint.objects.create(title="Pick your path", prompt="Where next?")
    basics = DecisionOption.objects.create(decision=decision, text="Basics", order=1)
    deeper_dive = DecisionOption.objects.create(decision=decision, text="Deeper dive", order=2)
    content = CourseContent.objects.create(
        course=course, priority=priority, type="decision", decision=decision, waiting_period=3600, is_published=True
    )
    return content, basics, deeper_dive


def make_lesson(course, priority, title, track=None):
    return CourseContent.objects.create(
        course=course,
        track=track,
        priority=priority,
        type="lesson",
        lesson=Lesson.objects.create(title=title, content="..."),
        waiting_period=3600,
        is_published=True,
    )


@pytest.fixture
def decision_delivery(db, course, active_enrollment):
    """A delivered decision on the spine, a Wrap up after it, and a "Deeper" track rejoining at Wrap up."""
    content, basics, deeper_dive = make_decision_content(course)
    wrap_up = make_lesson(course, 2, "Wrap up")
    deeper = ContentTrack.objects.create(course=course, name="Deeper", merge_into=wrap_up)
    deeper_lesson = make_lesson(course, 1, "Deeper lesson", track=deeper)
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=content)
    return SimpleNamespace(
        delivery=delivery,
        content=content,
        basics=basics,
        deeper_dive=deeper_dive,
        wrap_up=wrap_up,
        deeper=deeper,
        deeper_lesson=deeper_lesson,
    )


def token_for(delivery):
    return jwt_service.generate_jwt({"delivery_id": delivery.id, "delivery_hash": delivery.hash_value})


def answer(client, token, option_id):
    return client.post(URL, data={"token": token, "option_id": option_id}, content_type="application/json")


def route_on_deeper_dive(d):
    ContentTransition.objects.create(
        source=d.content, order=1, condition=TransitionCondition.OPTION_SELECTED, option=d.deeper_dive, target=d.deeper
    )


def scheduled_after(delivery):
    return ContentDelivery.objects.filter(enrollment=delivery.enrollment).exclude(id=delivery.id)


def test_the_chosen_answer_routes_the_learner_onto_its_track(decision_delivery, anonymous_client):
    d = decision_delivery
    route_on_deeper_dive(d)

    response = answer(anonymous_client, token_for(d.delivery), d.deeper_dive.id)

    assert response.status_code == 200
    assert DecisionResponse.objects.get(delivery=d.delivery).option == d.deeper_dive
    assert scheduled_after(d.delivery).get().course_content == d.deeper_lesson


def test_an_answer_no_rule_claims_continues_to_the_next_content(decision_delivery, anonymous_client):
    d = decision_delivery
    route_on_deeper_dive(d)

    answer(anonymous_client, token_for(d.delivery), d.basics.id)

    assert scheduled_after(d.delivery).get().course_content == d.wrap_up


def test_a_decision_without_rules_records_the_answer_and_moves_on(decision_delivery, anonymous_client):
    d = decision_delivery

    response = answer(anonymous_client, token_for(d.delivery), d.deeper_dive.id)

    assert response.status_code == 200
    assert DecisionResponse.objects.get(delivery=d.delivery).option == d.deeper_dive
    assert scheduled_after(d.delivery).get().course_content == d.wrap_up


def test_answering_the_last_content_completes_the_course(db, course, active_enrollment, anonymous_client):
    content, basics, _ = make_decision_content(course)
    delivery = ContentDelivery.objects.create(enrollment=active_enrollment, course_content=content)

    answer(anonymous_client, token_for(delivery), basics.id)

    active_enrollment.refresh_from_db()
    assert active_enrollment.status == EnrollmentStatus.COMPLETED
    assert not scheduled_after(delivery).exists()


def test_the_first_answer_retires_the_link(decision_delivery, anonymous_client):
    d = decision_delivery
    token = token_for(d.delivery)

    assert answer(anonymous_client, token, d.basics.id).status_code == 200
    second = answer(anonymous_client, token, d.deeper_dive.id)

    assert second.status_code == 410
    assert DecisionResponse.objects.get(delivery=d.delivery).option == d.basics
    assert scheduled_after(d.delivery).count() == 1


def test_answering_stops_the_reminders_and_the_deadline(decision_delivery, anonymous_client):
    d = decision_delivery
    d.delivery.remind_at = timezone.now()
    d.delivery.valid_until = timezone.now() + timezone.timedelta(days=2)
    d.delivery.save()

    answer(anonymous_client, token_for(d.delivery), d.basics.id)

    d.delivery.refresh_from_db()
    assert d.delivery.remind_at is None
    assert d.delivery.valid_until is None


def test_an_answer_from_another_decision_point_is_refused(decision_delivery, anonymous_client):
    d = decision_delivery
    elsewhere = DecisionOption.objects.create(
        decision=DecisionPoint.objects.create(title="Another question", prompt="?"), text="Elsewhere", order=1
    )

    response = answer(anonymous_client, token_for(d.delivery), elsewhere.id)

    assert response.status_code == 400
    assert not DecisionResponse.objects.exists()
    assert not scheduled_after(d.delivery).exists()


def test_an_inactive_enrollment_cannot_answer(decision_delivery, anonymous_client):
    d = decision_delivery
    enrollment = d.delivery.enrollment
    enrollment.status = EnrollmentStatus.DEACTIVATED
    enrollment.deactivation_reason = DeactivationReason.INACTIVE
    enrollment.save()

    response = answer(anonymous_client, token_for(d.delivery), d.basics.id)

    assert response.status_code == 400
    assert not DecisionResponse.objects.exists()


def test_an_invalid_token_is_refused(decision_delivery, anonymous_client):
    response = answer(anonymous_client, "not-a-token", decision_delivery.basics.id)

    assert response.status_code == 400
    assert not DecisionResponse.objects.exists()


def answer_in_email(client, settings, data, source_origin=None):
    return client.post(
        f"{AMP_URL}?__amp_source_origin={source_origin or email_sender_service.from_email}",
        data=data,
        HTTP_ORIGIN=settings.CSRF_TRUSTED_ORIGINS[0],
    )


def test_answering_in_the_email_routes_like_the_page(decision_delivery, anonymous_client, settings):
    d = decision_delivery
    route_on_deeper_dive(d)

    response = answer_in_email(
        anonymous_client, settings, {"token": token_for(d.delivery), "option_id": d.deeper_dive.id}
    )

    assert response.status_code == 200
    assert response["AMP-Access-Control-Allow-Source-Origin"] == email_sender_service.from_email
    assert DecisionResponse.objects.get(delivery=d.delivery).option == d.deeper_dive
    assert scheduled_after(d.delivery).get().course_content == d.deeper_lesson


def test_the_email_form_says_when_the_page_was_answered_first(decision_delivery, anonymous_client, settings):
    d = decision_delivery
    token = token_for(d.delivery)
    answer(anonymous_client, token, d.basics.id)

    response = answer_in_email(anonymous_client, settings, {"token": token, "option_id": d.deeper_dive.id})

    # The AMP headers are what let the form show the reason instead of a generic failure.
    assert response.status_code == 410
    assert response["AMP-Access-Control-Allow-Source-Origin"] == email_sender_service.from_email
    assert "already been answered" in response.json()["error"]
    assert DecisionResponse.objects.get(delivery=d.delivery).option == d.basics


def test_the_email_form_needs_a_chosen_answer(decision_delivery, anonymous_client, settings):
    response = answer_in_email(anonymous_client, settings, {"token": token_for(decision_delivery.delivery)})

    assert response.status_code == 400
    assert response["AMP-Access-Control-Allow-Source-Origin"] == email_sender_service.from_email
    assert not DecisionResponse.objects.exists()


def test_an_email_answer_from_an_untrusted_sender_is_refused(decision_delivery, anonymous_client, settings):
    d = decision_delivery

    response = answer_in_email(
        anonymous_client,
        settings,
        {"token": token_for(d.delivery), "option_id": d.basics.id},
        source_origin="attacker@evil.example.com",
    )

    assert response.status_code == 400
    assert not DecisionResponse.objects.exists()
