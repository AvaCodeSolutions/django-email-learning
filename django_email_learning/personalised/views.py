from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views import View
from django.views.generic.base import TemplateResponseMixin
from django.http import HttpResponse
from django.utils.translation import gettext as _
from django.utils.translation import get_language_info, get_language
from django.urls import reverse
from django_email_learning.models import ContentDelivery, EnrollmentStatus, Certificate
from django.utils import timezone
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
import logging
import io


@method_decorator(ensure_csrf_cookie, name="dispatch")
class BaseTemplateView(View, TemplateResponseMixin):
    def error_response(
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
        current_lang_code = get_language()
        lang_info = get_language_info(current_lang_code)
        return self.render_to_response(
            context={
                "appContext": {
                    "ref": error_ref,
                    "errorMessage": message,
                    "direction": "rtl" if lang_info["bidi"] else "ltr",
                    "localeMessages": {
                        "error": _("Error"),
                    },
                },
                "page_title": title,
            },
            status=status_code,
        )

    def get_decoded_token(self, request) -> dict | HttpResponse:  # type: ignore[no-untyped-def]
        try:
            token = request.GET["token"]
        except KeyError as e:
            return self.error_response(
                message=_("The link is not valid."),
                exception=e,
                status_code=400,
                title=_("Invalid Link"),
            )
        try:
            return jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as e:
            return self.error_response(
                message=_("The link is not valid."),
                exception=e,
                status_code=400,
                title=_("Invalid Link"),
            )
        except jwt_service.ExpiredTokenException as e:
            return self.error_response(
                message=_("The link has expired."),
                exception=e,
                status_code=410,
                title=_("Expired Link"),
            )

    def get_token_and_decoded_token(self, request) -> tuple[str, dict] | HttpResponse:  # type: ignore[no-untyped-def]
        decoded_token = self.get_decoded_token(request)
        if isinstance(decoded_token, HttpResponse):
            return decoded_token
        return request.GET.get("token", ""), decoded_token

    def get_app_context(self) -> dict:  # type: ignore[no-untyped-def]
        current_lang_code = get_language()
        lang_info = get_language_info(current_lang_code)
        return {
            "direction": "rtl" if lang_info["bidi"] else "ltr",
        }

    def delivery_from_token(self, request) -> ContentDelivery | HttpResponse:  # type: ignore[no-untyped-def]
        decoded_token = self.get_decoded_token(request)
        if isinstance(decoded_token, HttpResponse):
            return decoded_token  # Return error response if token is invalid
        try:
            delivery = ContentDelivery.objects.get(
                id=decoded_token["delivery_id"],
                hash_value=decoded_token["delivery_hash"],
            )
            return delivery
        except ContentDelivery.DoesNotExist as e:
            return self.error_response(
                message=_("The delivery does not exist."),
                exception=e,
                status_code=404,
                title=_("Invalid Delivery"),
            )


class AssignmentPublicView(BaseTemplateView):
    template_name = "personalised/assignment_public.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        token_and_decoded = self.get_token_and_decoded_token(request)
        if isinstance(token_and_decoded, HttpResponse):
            return token_and_decoded

        token, decoded_token = token_and_decoded
        try:
            delivery = ContentDelivery.objects.get(
                id=decoded_token["delivery_id"],
                hash_value=decoded_token["delivery_hash"],
            )
            enrollment = delivery.enrollment
            if enrollment.status != EnrollmentStatus.ACTIVE:
                return self.error_response(
                    message=_("This assignment is no longer valid."),
                    exception=ValueError("Enrollment is not active"),
                    title=_("Invalid Assignment"),
                )
            assignment = delivery.course_content.assignment
            if not assignment:
                return self.error_response(
                    message=_("There is no assignment associated with this link."),
                    exception=None,
                    title=_("Invalid Assignment"),
                )
            if not delivery.course_content.is_published:
                return self.error_response(
                    message=_(
                        "There is no valid assignment associated with this link."
                    ),
                    exception=ValueError("Assignment is not published"),
                    title=_("Invalid Assignment"),
                )
            assignment_data = {
                "id": assignment.id,
                "title": assignment.title,
                "description": assignment.description,
                "requires_file_submission": assignment.requires_file_submission,
                "requires_text_submission": assignment.requires_text_submission,
            }
            return self.render_to_response(
                context={
                    "appContext": {
                        "assignment": assignment_data,
                        "token": token,
                        "csrfToken": request.META.get("CSRF_COOKIE", ""),
                        "apiEndpoint": reverse(
                            "django_email_learning:api_personalised:assignment_submission"
                        ),
                        "fileUploadApiEndpoint": reverse(
                            "django_email_learning:api_personalised:file_upload"
                        ),
                        "localeMessages": {
                            "text_submission_label": _("Your Answer"),
                            "file_submission_label": _("Upload Your File"),
                            "submission_success": _(
                                "Your assignment has been submitted successfully!"
                            ),
                            "submission_error": _(
                                "An error occurred while submitting your assignment. Please try again later."
                            ),
                            "submit": _("Submit"),
                            "close_window_message": _("You can now close this window!"),
                        },
                    }
                    | self.get_app_context(),
                }
            )

        except ContentDelivery.DoesNotExist as e:
            if ContentDelivery.objects.filter(  # type: ignore[misc]
                id=decoded_token.get("delivery_id")
            ).exists():
                return self.render_to_response(
                    context={
                        "appContext": {
                            "errorMessage": _(
                                "The assignment link has already been used and is not valid anymore."
                            ),
                            "localeMessages": {
                                "close_window_message": _(
                                    "You can now close this window!"
                                ),
                            },
                        }
                    }
                )
            return self.error_response(
                message=_("An error occurred while retrieving the assignment"),
                exception=e,
                title=_("Error"),
                status_code=410,
            )


class QuizPublicView(BaseTemplateView):
    template_name = "personalised/quiz_public.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        token_and_decoded = self.get_token_and_decoded_token(request)
        if isinstance(token_and_decoded, HttpResponse):
            return token_and_decoded

        token, decoded_token = token_and_decoded
        try:
            question_ids = decoded_token.get("question_ids", [])
            delivery = ContentDelivery.objects.get(
                id=decoded_token["delivery_id"],
                hash_value=decoded_token["delivery_hash"],
            )
            enrollment = delivery.enrollment
            if enrollment.status != EnrollmentStatus.ACTIVE:
                return self.error_response(
                    message=_("This quiz is no longer valid."),
                    exception=ValueError("Enrollment is not active"),
                    title=_("Invalid Quiz"),
                )
            quiz = delivery.course_content.quiz
            if not quiz:
                return self.error_response(
                    message=_("There is no quiz associated with this link."),
                    exception=None,
                    title=_("Invalid Quiz"),
                )
            if not delivery.course_content.is_published:
                return self.error_response(
                    message=_("There is no valid quiz associated with this link."),
                    exception=ValueError("Quiz is not published"),
                    title=_("Invalid Quiz"),
                )
            quiz_data = PublicQuizSerializer.model_validate(quiz).model_dump()
            if question_ids:
                selected_questions = [
                    q for q in quiz_data["questions"] if q["id"] in question_ids
                ]
                # Only filter questions if all specified question IDs are valid and included in the quiz
                if len(selected_questions) == len(question_ids):
                    quiz_data["questions"] = selected_questions
            return self.render_to_response(
                context={
                    "appContext": {
                        "quiz": quiz_data,
                        "token": token,
                        "csrfToken": request.META.get("CSRF_COOKIE", ""),
                        "apiEndpoint": reverse(
                            "django_email_learning:api_personalised:quiz_submission"
                        ),
                        "localeMessages": {
                            "quiz_intro": _(
                                "Please select all correct answers for each question. Note that some questions may have multiple correct answers. This quiz uses negative marking for incorrect choices; if you are unsure, it is better to leave the question unanswered."
                            ),
                            "no_answer_warning": _(
                                "You have not selected any answers for this question. Are you sure you want to proceed?"
                            ),
                            "your_score": _("Your score"),
                            "error_loading_quiz": _("Error loading quiz"),
                            "ready_to_submit": _("Ready to submit?"),
                            "submit_quiz_note": _(
                                "Please keep in mind that this quiz uses negative marking for incorrect answers. If you are unsure of an answer, it may be better to leave it blank."
                            ),
                            "cancel": _("Cancel"),
                            "submit": _("Submit"),
                            "try_again": _("Try Again"),
                            "close_window_message": _("You can now close this window!"),
                            "non_blocking_quiz_caption": _(
                                "This quiz is for practice and does not affect your course progress. The course content will be sent to you regardless of your quiz answers."
                            ),
                        },
                    }
                    | self.get_app_context(),
                }
            )

        except ContentDelivery.DoesNotExist as e:
            if ContentDelivery.objects.filter(  # type: ignore[misc]
                id=decoded_token.get("delivery_id")
            ).exists():
                return self.render_to_response(
                    context={
                        "appContext": {
                            "errorMessage": _(
                                "The quiz link has already been used and is not valid anymore."
                            ),
                            "localeMessages": {
                                "error": _("Error"),
                            },
                        },
                        "page_title": _("Quiz Link Expired"),
                    },
                    status=410,
                )
            return self.error_response(
                message=_("An error occurred while retrieving the quiz"),
                exception=e,
                title=_("Error"),
                status_code=410,
            )


class CertificateFormView(BaseTemplateView):
    template_name = "personalised/certificate_form.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        decoded_token = self.get_decoded_token(request)
        if isinstance(decoded_token, HttpResponse):
            return decoded_token  # Return error response if token is invalid

        return self.render_to_response(
            context={
                "appContext": {
                    "csrfToken": request.META.get("CSRF_COOKIE", ""),
                    "token": request.GET.get("token", ""),
                    "apiEndpoint": reverse(
                        "django_email_learning:api_personalised:submit_certificate_form"
                    ),
                    "localeMessages": {
                        "form_title": _("Certificate of Completion"),
                        "form_intro": _(
                            "Congratulations on completing the course! To issue your certificate, please enter the name you would like displayed on it."
                        ),
                        "full_name": _("Full Name"),
                        "full_name_required": _("Full Name is required"),
                        "error_sending_data": _(
                            "An error occurred while sending data. Please try again later."
                        ),
                        "form_submission_success": _(
                            "Your certificate name has been submitted successfully!"
                        ),
                        "submit": _("Submit"),
                        "view_certificate": _("View Certificate"),
                    },
                }
                | self.get_app_context(),
            }
        )


class VerifyEnrollmentView(BaseTemplateView):
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
            return self.error_response(
                message=_("An error occurred during enrollment verification."),
                exception=e,
                title=_("Verification Error"),
            )

        return self.render_to_response(
            context={
                "page_title": _("Enrollment Verified"),
                "appContext": {
                    "successMessage": _(
                        "Your enrollment has been successfully verified."
                    ),
                    "localeMessages": {"Confirm": _("Confirm")},
                }
                | self.get_app_context(),
            }
        )


class UnsubscribeView(BaseTemplateView):
    template_name = "personalised/command_result.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        decoded_token = self.get_decoded_token(request)
        if isinstance(decoded_token, HttpResponse):
            return decoded_token  # Return error response if token is invalid
        if request.GET.get("confirm") != "true":
            return self.render_to_response(
                context={
                    "page_title": _("Confirm Unsubscription"),
                    "appContext": {
                        "confirmationMessage": _(
                            "Are you sure you want to unsubscribe from our mailing list?"
                        ),
                        "confirmUrl": f"{request.path}?token={request.GET.get('token')}&confirm=true",
                        "localeMessages": {"Confirm": _("Confirm")},
                    }
                    | self.get_app_context(),
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
            return self.error_response(
                message=_("An error occurred during unsubscription."),
                exception=e,
                title=_("Unsubscription Error"),
            )
        return self.render_to_response(
            context={
                "page_title": _("Unsubscribed"),
                "appContext": {
                    "successMessage": _(
                        "You have been successfully unsubscribed from our mailing list."
                    ),
                    "localeMessages": {"Confirm": _("Confirm")},
                }
                | self.get_app_context(),
            }
        )


class CertificateView(BaseTemplateView):
    template_name = "personalised/certificate.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        certificate_number = kwargs.get("certificate_number")
        if not certificate_number:
            return self.error_response(
                message=_("Certificate number is required."),
                exception=ValueError("Certificate number is required"),
                status_code=400,
                title=_("Invalid Certificate"),
            )
        id_parts = certificate_number.split("-")
        if len(id_parts) != 4:
            return self.error_response(
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
            return self.error_response(
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
                "page_title": f"{_('Certificate of Completion')} | {certificate.enrollment.course.title} | {certificate.name_on_certificate}",
                "appContext": {
                    "name": certificate.name_on_certificate,
                    "courseTitle": certificate.enrollment.course.title,
                    "issueDate": certificate.issued_at.strftime("%B %d, %Y"),
                    "certificateNumber": certificate_number,
                    "organizationName": certificate.enrollment.course.organization.name,
                    "logoUrl": certificate.enrollment.course.organization.logo.url
                    if certificate.enrollment.course.organization.logo
                    else "",
                    "qrcodeUrl": absolute_media_url,
                    "localeMessages": {
                        "title": _("Certificate of Completion"),
                        "description": _(
                            "This certifies that {name} has successfully completed the {course_title} course"
                        ).format(
                            name=certificate.name_on_certificate,
                            course_title=certificate.enrollment.course.title,
                        ),
                        "issue_date": _("Issued on"),
                        "certificate_number": _("Certificate Number"),
                        "organization_team": _("{organization_name} Team").format(
                            organization_name=certificate.enrollment.course.organization.name
                        ),
                    },
                }
                | self.get_app_context(),
            }
        )


# 1×1 transparent GIF (43 bytes)
_TRANSPARENT_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00"
    b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
    b"\x44\x01\x00\x3b"
)


class TrackOpenView(View):
    """
    Records the first open of a content delivery email.
    Used both as a tracking pixel (HTML emails) and via <amp-pixel> (AMP emails).
    Always returns a 1×1 transparent GIF so email clients don't show a broken image.
    """

    def get(self, request, hash_value: str, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        try:
            delivery = ContentDelivery.objects.get(hash_value=hash_value)
            if delivery.opened_at is None:
                delivery.opened_at = timezone.now()
                delivery.save(update_fields=["opened_at"])
        except ContentDelivery.DoesNotExist:
            pass  # Invalid hash — still return the pixel, don't error

        return HttpResponse(_TRANSPARENT_GIF, content_type="image/gif")
