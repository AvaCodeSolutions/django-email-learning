from django_email_learning.models import DeliverySchedule, ContentDelivery
from urllib.parse import urlparse, parse_qs
from django_email_learning.services import jwt_service
from django.conf import settings
import jwt
from datetime import datetime


def test_generate_link(course_quiz_content, enrollment):
    content_delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_quiz_content,
    )
    delivery_schedule = DeliverySchedule.objects.create(delivery=content_delivery)
    link = delivery_schedule.generate_link()
    assert link.startswith("http")  # Assuming the link is a URL
    parsed_url = urlparse(link)
    query_string = parsed_url.query
    query_params = parse_qs(query_string)
    assert "token" in query_params
    decoded_token = jwt_service.decode_jwt(query_params["token"][0])
    assert decoded_token["delivery_id"] == delivery_schedule.id
    assert decoded_token["delivery_hash"] == content_delivery.hash_value


def test_generate_link_for_assignment_content(course_assignment_content, enrollment):
    content_delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    delivery_schedule = DeliverySchedule.objects.create(delivery=content_delivery)

    link = delivery_schedule.generate_link()

    assert link.startswith("http")
    parsed_url = urlparse(link)
    query_params = parse_qs(parsed_url.query)
    assert "token" in query_params

    decoded_token = jwt_service.decode_jwt(query_params["token"][0])
    assert decoded_token["delivery_id"] == delivery_schedule.id
    assert decoded_token["delivery_hash"] == content_delivery.hash_value


def test_generate_link_assignment_with_zero_deadline_uses_datetime_max_exp(
    course_assignment_content, enrollment
):
    course_assignment_content.assignment.deadline_days = 0
    course_assignment_content.assignment.save()

    content_delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_assignment_content,
    )
    delivery_schedule = DeliverySchedule.objects.create(delivery=content_delivery)

    link = delivery_schedule.generate_link()
    token = parse_qs(urlparse(link).query)["token"][0]
    decoded_token = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=["HS256"],
        options={"verify_exp": False},
    )

    expected_token = jwt_service.generate_jwt(
        payload={"placeholder": 1},
        exp=datetime.max,
    )
    expected_decoded = jwt.decode(
        expected_token,
        settings.SECRET_KEY,
        algorithms=["HS256"],
        options={"verify_exp": False},
    )

    assert decoded_token["exp"] == expected_decoded["exp"]
