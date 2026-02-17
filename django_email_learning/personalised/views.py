from django.views import View
from django.views.generic.base import TemplateResponseMixin
from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.urls import reverse
from django_email_learning.models import ContentDelivery, EnrollmentStatus, Certificate
from django_email_learning.services import jwt_service
from django_email_learning.personalised.serializers import PublicQuizSerializer
from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)
from django_email_learning.services.command_models.unsubscribe_command import (
    UnsubscribeCommand,
)
from django.core.files.storage import default_storage
import qrcode
import uuid
import json
import logging
import io


class ErrrorLoggingMixin(TemplateResponseMixin):
    def errr_response(
        self,
        message: str,
        exception: Exception | None,
        status_code: int = 500,
        title: str = _("Error"),
    ) -> HttpResponse:
        error_ref = uuid.uuid4().hex
        if exception:
            logging.exception(
                f"{message} - Ref: {error_ref}", extra={"error_ref": error_ref}
            )
        else:
            logging.error(
                f"{message} - Ref: {error_ref}", extra={"error_ref": error_ref}
            )
        return self.render_to_response(
            context={"ref": error_ref, "error_message": message, "page_title": title},
            status=status_code,
        )

    def get_decoded_token(self, request) -> dict | HttpResponse:  # type: ignore[no-untyped-def]
        try:
            token = request.GET["token"]
        except KeyError as e:
            return self.errr_response(
                message=_("The link is not valid."),
                exception=e,
                status_code=400,
                title=_("Invalid Link"),
            )
        try:
            return jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as e:
            return self.errr_response(
                message=_("The link is not valid."),
                exception=e,
                status_code=400,
                title=_("Invalid Link"),
            )
        except jwt_service.ExpiredTokenException as e:
            return self.errr_response(
                message=_("The link has expired."),
                exception=e,
                status_code=410,
                title=_("Expired Link"),
            )


class QuizPublicView(View, ErrrorLoggingMixin):
    template_name = "personalised/quiz_public.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        try:
            token = request.GET["token"]
            decoded_token = self.get_decoded_token(request)
            if isinstance(decoded_token, HttpResponse):
                return decoded_token  # Return error response if token is invalid
            question_ids = decoded_token.get("question_ids", [])
            delivery = ContentDelivery.objects.get(
                id=decoded_token["delivery_id"],
                hash_value=decoded_token["delivery_hash"],
            )
            enrolment = delivery.enrollment
            if enrolment.status != EnrollmentStatus.ACTIVE:
                return self.errr_response(
                    message=_("Quiz is not valid anymore"),
                    exception=ValueError("Enrolment is not active"),
                    title=_("Invalid Quiz"),
                )
            quiz = delivery.course_content.quiz
            if not quiz:
                return self.errr_response(
                    message=_("No quiz associated with this link"),
                    exception=None,
                    title=_("Invalid Quiz"),
                )
            if not delivery.course_content.is_published:
                return self.errr_response(
                    message=_("No valid quiz associated with this link"),
                    exception=ValueError("Quiz is not published"),
                    title=_("Invalid Quiz"),
                )
            quiz_data = PublicQuizSerializer.model_validate(quiz).model_dump()
            if question_ids:
                quiz_data["questions"] = [
                    q for q in quiz_data["questions"] if q["id"] in question_ids
                ]
            return self.render_to_response(
                context={
                    "quiz": json.dumps(quiz_data),
                    "token": token,
                    "csrf_token": request.META.get("CSRF_COOKIE", ""),
                    "api_endpoint": reverse(
                        "django_email_learning:api_personalised:quiz_submission"
                    ),
                }
            )

        except ContentDelivery.DoesNotExist as e:
            return self.errr_response(
                message=_("An error occurred while retrieving the quiz"),
                exception=e,
                title=_("Error"),
            )
        except KeyError as e:
            return self.errr_response(
                message=_("The link is not valid"),
                exception=e,
                status_code=400,
                title=_("Invalid Link"),
            )
        except jwt_service.InvalidTokenException as e:
            return self.errr_response(
                message=_("The link is not valid"),
                exception=e,
                status_code=400,
                title=_("Invalid Link"),
            )
        except jwt_service.ExpiredTokenException as e:
            return self.errr_response(
                message=_("The link has expired"),
                exception=e,
                status_code=410,
                title=_("Expired Link"),
            )


class CertificateFormView(View, ErrrorLoggingMixin):
    template_name = "personalised/certificate_form.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        decoded_token = self.get_decoded_token(request)
        if isinstance(decoded_token, HttpResponse):
            return decoded_token  # Return error response if token is invalid

        return self.render_to_response(
            context={
                "enrollment_id": decoded_token["enrollment_id"],
                "csrf_token": request.META.get("CSRF_COOKIE", ""),
                "token": request.GET.get("token", ""),
                "api_endpoint": reverse(
                    "django_email_learning:api_personalised:submit_certificate_form"
                ),
            }
        )


class VerifyEnrollmentView(View, ErrrorLoggingMixin):
    template_name = "personalised/command_result.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        decoded_token = self.get_decoded_token(request)
        if isinstance(decoded_token, HttpResponse):
            return decoded_token  # Return error response if token is invalid
        enrollment_id = decoded_token["enrollment_id"]
        verification_code = decoded_token["verification_code"]

        command = VerifyEnrollmentCommand(
            command_name="verify_enrollment",
            enrollment_id=enrollment_id,
            verification_code=verification_code,
        )
        try:
            command.execute()
        except Exception as e:
            return self.errr_response(
                message=_("An error occurred during enrollment verification."),
                exception=e,
                title=_("Verification Error"),
            )

        return self.render_to_response(
            context={
                "page_title": _("Enrollment Verified"),
                "success_message": _("Your enrollment has been successfully verified."),
            }
        )


class UnsubscribeView(View, ErrrorLoggingMixin):
    template_name = "personalised/command_result.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        decoded_token = self.get_decoded_token(request)
        if isinstance(decoded_token, HttpResponse):
            return decoded_token  # Return error response if token is invalid
        if request.GET.get("confirm") != "true":
            return self.render_to_response(
                context={
                    "page_title": _("Confirm Unsubscription"),
                    "confirmation_message": _(
                        "Are you sure you want to unsubscribe from our mailing list?"
                    ),
                    "confirm_url": f"{request.path}?token={request.GET.get('token')}&confirm=true",
                }
            )
        command = UnsubscribeCommand(
            email=decoded_token["email"],
            course_slug=decoded_token["course_slug"],
            organization_id=decoded_token["organization_id"],
        )
        try:
            command.execute()
        except Exception as e:
            return self.errr_response(
                message=_("An error occurred during unsubscription."),
                exception=e,
                title=_("Unsubscription Error"),
            )
        return self.render_to_response(
            context={
                "page_title": _("Unsubscribed"),
                "success_message": _(
                    "You have been successfully unsubscribed from our mailing list."
                ),
            }
        )


class CertificateView(View, ErrrorLoggingMixin):
    template_name = "personalised/certificate.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        certificate_number = kwargs.get("certificate_number")
        if not certificate_number:
            return self.errr_response(
                message=_("Certificate number is required."),
                exception=ValueError("Certificate number is required"),
                status_code=400,
                title=_("Invalid Certificate"),
            )
        id_parts = certificate_number.split("-")
        if len(id_parts) != 4:
            return self.errr_response(
                message=_("Invalid certificate number format."),
                exception=ValueError("Invalid certificate number format"),
                status_code=400,
                title=_("Invalid Certificate"),
            )
        certificate_id = id_parts[2]
        random_suffix = id_parts[3]
        try:
            certificate = Certificate.objects.get(
                id=certificate_id, random_suffix=random_suffix
            )
        except Certificate.DoesNotExist:
            return self.errr_response(
                message=_("Certificate not found."),
                exception=ValueError("Certificate not found"),
                status_code=404,
                title=_("Certificate Not Found"),
            )

        path = reverse(
            "django_email_learning:personalised:certificate",
            kwargs={"certificate_number": certificate_number},
        )
        full_url = request.build_absolute_uri(path)

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(full_url)
        qr.make(fit=True)

        qrcode_img = qr.make_image(
            fill_color="black", back_color="transparent"
        ).convert("RGBA")  # type: ignore[union-attr]

        img_byte_arr = io.BytesIO()
        qrcode_img.save(img_byte_arr, format="PNG")

        media_path = f"certificates/{certificate.enrollment.course.organization.id}/{certificate_number}.png"
        default_storage.save(media_path, img_byte_arr)
        absolute_media_url = default_storage.url(media_path)

        return self.render_to_response(
            context={
                "page_title": f"{_("Certificate of Completion")} | {certificate.enrollment.course.title} | {certificate.name_on_certificate}",
                "name": certificate.name_on_certificate.upper(),
                "course_title": certificate.enrollment.course.title,
                "issue_date": certificate.issued_at.strftime("%B %d, %Y"),
                "certificate_number": certificate_number,
                "organization_name": certificate.enrollment.course.organization.name,
                "logo_url": certificate.enrollment.course.organization.logo.url
                if certificate.enrollment.course.organization.logo
                else "",
                "qrcode_url": absolute_media_url,
            }
        )
