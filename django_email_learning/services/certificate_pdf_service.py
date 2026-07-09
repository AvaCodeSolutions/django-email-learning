import base64
import io
import mimetypes

import qrcode
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse

from django_email_learning.models import Certificate, Organization


def _qrcode_data_uri(url: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")  # type: ignore[union-attr]

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _logo_data_uri(organization: Organization) -> str | None:
    if not organization.logo:
        return None
    content_type = mimetypes.guess_type(str(organization.logo.name))[0] or "image/png"
    with organization.logo.open("rb") as logo_file:
        encoded = base64.b64encode(logo_file.read()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def _render_html_to_pdf(html: str) -> bytes:
    from weasyprint import HTML  # type: ignore[import-untyped]

    return HTML(string=html).write_pdf()  # type: ignore[no-any-return]


def generate_certificate_pdf(certificate: Certificate) -> bytes:
    """
    Renders a Certificate as a PDF, embedding the organization logo and a
    verification QR code as base64 data URIs so generation doesn't depend on
    network access or the storage backend being publicly reachable.

    Requires the "certificates" optional dependency group (WeasyPrint).
    """
    course = certificate.enrollment.course
    organization = course.organization

    certificate_path = reverse(
        "django_email_learning:personalised:certificate",
        kwargs={"certificate_number": certificate.certificate_number},
    )
    certificate_url = f"{settings.DJANGO_EMAIL_LEARNING['SITE_BASE_URL']}{certificate_path}"

    html = render_to_string(
        "certificates/certificate_pdf.html",
        {
            "name": certificate.name_on_certificate,
            "course_title": course.title,
            "organization_name": organization.name,
            "issue_date": certificate.issued_at.strftime("%B %d, %Y"),
            "certificate_number": certificate.certificate_number,
            "qrcode_data_uri": _qrcode_data_uri(certificate_url),
            "logo_data_uri": _logo_data_uri(organization),
        },
    )
    return _render_html_to_pdf(html)
