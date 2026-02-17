from django.urls import reverse
from django_email_learning.models import Certificate
import pytest


def get_url(certificate_number):
    return reverse(
        "django_email_learning:personalised:certificate",
        kwargs={"certificate_number": certificate_number},
    )


@pytest.fixture
def certificate(enrollment):
    return Certificate.objects.create(
        enrollment=enrollment, name_on_certificate="John Doe"
    )


def test_certificate_view(certificate, anonymous_client):
    url = get_url(certificate.certificate_number)
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert "page_title" in response.context
    assert (
        response.context["page_title"]
        == f"Certificate of Completion | {certificate.enrollment.course.title} | John Doe"
    )
    assert response.context["name"] == certificate.name_on_certificate.upper()
    assert response.context["course_title"] == certificate.enrollment.course.title
    assert response.context["issue_date"] == certificate.issued_at.strftime("%B %d, %Y")
