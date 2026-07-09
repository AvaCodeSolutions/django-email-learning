from unittest.mock import patch

import pytest

from django_email_learning.models import Certificate
from django_email_learning.services.certificate_pdf_service import generate_certificate_pdf


@pytest.fixture
def certificate(enrollment):
    return Certificate.objects.create(enrollment=enrollment, name_on_certificate="John Doe")


def test_generate_certificate_pdf_returns_rendered_output(certificate):
    with patch(
        "django_email_learning.services.certificate_pdf_service._render_html_to_pdf",
        return_value=b"%PDF-1.4 fake pdf bytes",
    ) as render_mock:
        result = generate_certificate_pdf(certificate)

    assert result == b"%PDF-1.4 fake pdf bytes"
    render_mock.assert_called_once()
    rendered_html = render_mock.call_args.args[0]
    assert certificate.name_on_certificate in rendered_html
    assert certificate.enrollment.course.title in rendered_html
    assert certificate.certificate_number in rendered_html


def test_generate_certificate_pdf_without_organization_logo(certificate):
    assert not certificate.enrollment.course.organization.logo

    with patch(
        "django_email_learning.services.certificate_pdf_service._render_html_to_pdf",
        return_value=b"%PDF-1.4 fake pdf bytes",
    ):
        result = generate_certificate_pdf(certificate)

    assert result == b"%PDF-1.4 fake pdf bytes"
