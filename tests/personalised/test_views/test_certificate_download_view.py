from unittest.mock import patch

import pytest
from django.urls import reverse

from django_email_learning.models import Certificate


def get_url(certificate_number):
    return reverse(
        "django_email_learning:personalised:certificate_download",
        kwargs={"certificate_number": certificate_number},
    )


@pytest.fixture
def certificate(enrollment):
    return Certificate.objects.create(enrollment=enrollment, name_on_certificate="John Doe")


def test_certificate_download_view_returns_pdf(certificate, anonymous_client):
    with patch(
        "django_email_learning.personalised.views.generate_certificate_pdf",
        return_value=b"%PDF-1.4 fake pdf bytes",
    ) as generate_mock:
        response = anonymous_client.get(get_url(certificate.certificate_number))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"] == f'attachment; filename="certificate-{certificate.certificate_number}.pdf"'
    assert response.content == b"%PDF-1.4 fake pdf bytes"
    generate_mock.assert_called_once_with(certificate)


def test_certificate_download_view_not_found(db, anonymous_client):
    response = anonymous_client.get(get_url("1-1-9999-123456"))
    assert response.status_code == 404


def test_certificate_download_view_invalid_format(db, anonymous_client):
    response = anonymous_client.get(get_url("not-a-valid-number"))
    assert response.status_code == 400
