import pytest
from django.urls import reverse

from django_email_learning.models import ContentDelivery, CourseContent, DecisionOption, DecisionPoint
from django_email_learning.services import jwt_service

URL = reverse("django_email_learning:personalised:decision_public_view")


@pytest.fixture
def decision_delivery(db, course, active_enrollment):
    decision = DecisionPoint.objects.create(title="Pick your path", prompt="Where next?")
    DecisionOption.objects.create(decision=decision, text="Deeper dive", order=2)
    DecisionOption.objects.create(decision=decision, text="Basics", order=1)
    content = CourseContent.objects.create(
        course=course, priority=1, type="decision", decision=decision, waiting_period=3600, is_published=True
    )
    return ContentDelivery.objects.create(enrollment=active_enrollment, course_content=content)


def token_for(delivery):
    return jwt_service.generate_jwt({"delivery_id": delivery.id, "delivery_hash": delivery.hash_value})


def test_the_page_shows_the_question_and_its_answers_in_order(decision_delivery, anonymous_client):
    response = anonymous_client.get(f"{URL}?token={token_for(decision_delivery)}")

    assert response.status_code == 200
    app_context = response.context["appContext"]
    assert app_context["decision"]["title"] == "Pick your path"
    assert app_context["decision"]["prompt"] == "Where next?"
    assert [option["text"] for option in app_context["decision"]["options"]] == ["Basics", "Deeper dive"]
    assert app_context["apiEndpoint"] == reverse("django_email_learning:api_personalised:decision_submission")


def test_the_page_shows_only_what_a_learner_picks_from(decision_delivery, anonymous_client):
    response = anonymous_client.get(f"{URL}?token={token_for(decision_delivery)}")

    options = response.context["appContext"]["decision"]["options"]
    assert all(set(option) == {"id", "text"} for option in options)


def test_an_answered_decision_says_so(decision_delivery, anonymous_client):
    token = token_for(decision_delivery)
    decision_delivery.update_hash()

    response = anonymous_client.get(f"{URL}?token={token}")

    assert response.status_code == 410
    assert "already been answered" in response.content.decode()


def test_an_unpublished_decision_is_not_shown(decision_delivery, anonymous_client):
    content = decision_delivery.course_content
    content.is_published = False
    content.save()

    response = anonymous_client.get(f"{URL}?token={token_for(decision_delivery)}")

    assert "decision" not in response.context["appContext"]
    assert "no valid question" in response.content.decode()


def test_a_link_for_other_content_is_refused(content_delivery, anonymous_client):
    response = anonymous_client.get(f"{URL}?token={token_for(content_delivery)}")

    assert "decision" not in response.context["appContext"]
    assert "no question associated" in response.content.decode()


def test_an_invalid_token_is_refused(anonymous_client):
    response = anonymous_client.get(f"{URL}?token=invalidtoken")

    assert response.status_code == 400
