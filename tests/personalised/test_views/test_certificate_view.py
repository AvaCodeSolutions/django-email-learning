import pytest
from django.urls import reverse

from django_email_learning.models import Certificate


def get_url(certificate_number):
    return reverse(
        "django_email_learning:personalised:certificate",
        kwargs={"certificate_number": certificate_number},
    )


@pytest.fixture
def certificate(enrollment):
    return Certificate.objects.create(enrollment=enrollment, name_on_certificate="John Doe")


def test_certificate_view(certificate, anonymous_client):
    url = get_url(certificate.certificate_number)
    response = anonymous_client.get(url)

    assert response.status_code == 200
    assert "page_title" in response.context
    assert (
        response.context["page_title"]
        == f"Certificate of Completion | {certificate.enrollment.course.title} | John Doe"
    )
    assert response.context["appContext"]["name"] == certificate.name_on_certificate
    assert response.context["appContext"]["courseTitle"] == certificate.enrollment.course.title
    assert response.context["appContext"]["issueDate"] == certificate.issued_at.strftime("%B %d, %Y")


def test_certificate_view_passes_the_issued_custom_fields(enrollment, anonymous_client):
    certificate = Certificate.objects.create(
        enrollment=enrollment,
        name_on_certificate="John Doe",
        custom_fields=[{"label": "CPD Points", "value": "5"}],
    )

    response = anonymous_client.get(get_url(certificate.certificate_number))

    assert response.status_code == 200
    assert response.context["appContext"]["customFields"] == [{"label": "CPD Points", "value": "5"}]


def test_certificate_view_without_custom_fields(certificate, anonymous_client):
    response = anonymous_client.get(get_url(certificate.certificate_number))

    assert response.status_code == 200
    assert response.context["appContext"]["customFields"] == []
