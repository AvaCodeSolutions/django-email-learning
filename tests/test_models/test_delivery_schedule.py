from django_email_learning.models import DeliverySchedule, ContentDelivery
from urllib.parse import urlparse, parse_qs
from django_email_learning.services import jwt_service


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
