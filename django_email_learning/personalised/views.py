from django.views import View
from django.views.generic.base import TemplateResponseMixin
from django.http import HttpResponse
from django.urls import reverse
from django_email_learning.models import ContentDelivery, EnrollmentStatus
from django_email_learning.services import jwt_service
from django_email_learning.personalised.serializers import PublicQuizSerializer
from django_email_learning.services.command_models.verify_enrollment_command import (
    VerifyEnrollmentCommand,
)
import uuid
import logging


class ErrrorLoggingMixin(TemplateResponseMixin):
    def errr_response(
        self, message: str, exception: Exception | None, status_code: int = 500
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
            context={"ref": error_ref, "error_message": message}, status=status_code
        )


class QuizPublicView(View, ErrrorLoggingMixin):
    template_name = "personalised/quiz_public.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        try:
            token = request.GET["token"]
            decoded = jwt_service.decode_jwt(token=token)
            question_ids = decoded.get("question_ids", [])
            delivery = ContentDelivery.objects.get(
                id=decoded["delivery_id"], hash_value=decoded["delivery_hash"]
            )
            enrolment = delivery.enrollment
            if enrolment.status != EnrollmentStatus.ACTIVE:
                return self.errr_response(
                    message="Quiz is not valid anymore",
                    exception=ValueError("Enrolment is not active"),
                )
            quiz = delivery.course_content.quiz
            if not quiz:
                return self.errr_response(
                    message="No quiz associated with this link", exception=None
                )
            if not delivery.course_content.is_published:
                return self.errr_response(
                    message="No valid quiz associated with this link",
                    exception=ValueError("Quiz is not published"),
                )
            quiz_data = PublicQuizSerializer.model_validate(quiz).model_dump()
            if question_ids:
                quiz_data["questions"] = [
                    q for q in quiz_data["questions"] if q["id"] in question_ids
                ]
            return self.render_to_response(
                context={
                    "quiz": quiz_data,
                    "token": token,
                    "csrf_token": request.META.get("CSRF_COOKIE", ""),
                    "api_endpoint": reverse(
                        "django_email_learning:api_personalised:quiz_submission"
                    ),
                }
            )

        except ContentDelivery.DoesNotExist as e:
            return self.errr_response(
                message="An error occurred while retrieving the quiz", exception=e
            )
        except KeyError as e:
            return self.errr_response(
                message="The link is not valid", exception=e, status_code=400
            )
        except jwt_service.InvalidTokenException as e:
            return self.errr_response(
                message="The link is not valid", exception=e, status_code=400
            )
        except jwt_service.ExpiredTokenException as e:
            return self.errr_response(
                message="The link has expired", exception=e, status_code=410
            )


class VerifyEnrollmentView(View, ErrrorLoggingMixin):
    template_name = "personalised/verify_enrollment.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:  # type: ignore[no-untyped-def]
        try:
            token = request.GET["token"]
        except KeyError as e:
            return self.errr_response(
                message="The verification link is not valid.",
                exception=e,
                status_code=400,
            )
        try:
            decoded = jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as e:
            return self.errr_response(
                message="The verification link is not valid.",
                exception=e,
                status_code=400,
            )
        except jwt_service.ExpiredTokenException as e:
            return self.errr_response(
                message="The verification link has expired.",
                exception=e,
                status_code=410,
            )

        enrollment_id = decoded["enrollment_id"]
        verification_code = decoded["verification_code"]

        command = VerifyEnrollmentCommand(
            command_name="verify_enrollment",
            enrollment_id=enrollment_id,
            verification_code=verification_code,
        )
        try:
            command.execute()
        except Exception as e:
            return self.errr_response(
                message="An error occurred during enrollment verification.", exception=e
            )

        return self.render_to_response(context={"page_title": "Enrollment Verified"})
