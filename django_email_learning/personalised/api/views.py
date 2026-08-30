import json
import logging
import urllib.parse
import uuid

from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from django_email_learning.models import (
    AssignmentSubmission,
    Certificate,
    ContentDelivery,
    Enrollment,
    EnrollmentStatus,
    Quiz,
    QuizSubmission,
)
from django_email_learning.personalised.api.serializers import (
    QuestionResponse,
    QuizSubmissionRequest,
)
from django_email_learning.services import jwt_service
from django_email_learning.services.email_sender_service import email_sender_service
from django_email_learning.services.metrics_service import metric_service
from django_email_learning.services.sanitize import strip_html
from django_email_learning.services.utils import PRIVATE_FILE_STORAGE

logger = logging.getLogger(__name__)


def _is_trusted_amp_sender(source_origin: str) -> bool:
    """An AMP form submission is trusted when its sender address is the platform
    default FROM_EMAIL, or - when domain-wide email is enabled - any address at
    the configured sending domain (courses using the organization option send
    from ``org-slug-id@<domain>``).
    """
    origin = source_origin.lower()
    if origin and origin in email_sender_service.from_email.lower():
        return True
    conf = getattr(settings, "DJANGO_EMAIL_LEARNING", {}).get("DOMAIN_WIDE_EMAIL", {})
    domain = conf.get("DOMAIN")
    if conf.get("ENABLED") and domain and origin.endswith(f"@{domain.lower()}"):
        return True
    return False


class FileUploadView(View):
    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        token = request.POST.get("token")
        uploaded_file = request.FILES.get("file")

        if not token:
            return JsonResponse({"error": _("Token is required.")}, status=400)

        if not uploaded_file:
            return JsonResponse({"error": _("No file uploaded.")}, status=400)

        try:
            decoded = jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as jde:
            error_reference = uuid.uuid4()
            logger.warning(f"Invalid token error: {str(jde)} (error_id: {error_reference})")
            return JsonResponse({"error": "Invalid token", "error_id": str(error_reference)}, status=400)
        except jwt_service.ExpiredTokenException as ete:
            error_reference = uuid.uuid4()
            logger.warning(f"Expired token error: {str(ete)} (error_id: {error_reference})")
            return JsonResponse({"error": "Token is expired", "error_id": str(error_reference)}, status=410)

        try:
            delivery = ContentDelivery.objects.get(
                id=decoded["delivery_id"],
                hash_value=decoded["delivery_hash"],
            )
        except ContentDelivery.DoesNotExist:
            logger.error(
                f"File upload failed: No content delivery found for ID {decoded['delivery_id']} with provided hash."
            )
            return JsonResponse(
                {"error": "The content delivery associated with this token does not exist."},
                status=422,
            )

        if delivery.enrollment.status != EnrollmentStatus.ACTIVE:
            return JsonResponse({"error": _("File upload is not valid anymore")}, status=400)

        date_prefix = timezone.now().strftime("%Y%m%d")
        file_path = PRIVATE_FILE_STORAGE.save(
            f"uploads/{date_prefix}/{delivery.enrollment.course.organization.id}/{delivery.id}/{uploaded_file.name}",
            uploaded_file,
        )

        return JsonResponse(
            {
                "file_path": file_path,
                "file_name": uploaded_file.name,
            },
            status=201,
        )


class AssignmentSubmissionView(View):
    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        token = payload.get("token")
        text_submission = payload.get("text_submission")
        file_submission = payload.get("file_path")

        if not text_submission and not file_submission:
            return JsonResponse(
                {"error": _("At least one of text submission or file submission is required.")},
                status=400,
            )

        try:
            decoded = jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as jde:
            error_reference = uuid.uuid4()
            logger.warning(f"Invalid token error: {str(jde)} (error_id: {error_reference})")
            return JsonResponse({"error": "Invalid token", "error_id": str(error_reference)}, status=400)
        except jwt_service.ExpiredTokenException as ete:
            error_reference = uuid.uuid4()
            logger.warning(f"Expired token error: {str(ete)} (error_id: {error_reference})")
            return JsonResponse({"error": "Token is expired", "error_id": str(error_reference)}, status=410)

        delivery_id = decoded["delivery_id"]
        try:
            delivery = ContentDelivery.objects.get(id=delivery_id, hash_value=decoded["delivery_hash"])
        except ContentDelivery.DoesNotExist:
            logger.error(
                f"Assignment submission failed: No content delivery found for ID {delivery_id} with provided hash."
            )
            return JsonResponse(
                {"error": "The content delivery associated with this token does not exist."},
                status=422,
            )

        existing_submission = AssignmentSubmission.objects.filter(delivery=delivery).first()
        if (
            existing_submission
            and existing_submission.status != AssignmentSubmission.SubmissionStatus.REQUESTING_CHANGES
        ):
            return JsonResponse(
                {
                    "error": _(
                        "There is already a submission for this assignment."
                        " Please wait for it to be reviewed before submitting again."
                    )
                },
                status=400,
            )

        enrollment = delivery.enrollment
        if enrollment.status != EnrollmentStatus.ACTIVE:
            return JsonResponse({"error": "Assignment submission is not valid anymore"}, status=400)

        assignment = delivery.course_content.assignment
        if not assignment:
            logger.error(f"Assignment submission failed: No assignment found for content delivery ID {delivery_id}.")
            return JsonResponse({"error": "No assignment associated with this link"}, status=422)

        if assignment.requires_text_submission and not text_submission:
            return JsonResponse(
                {"error": _("Text submission is required for this assignment.")},
                status=400,
            )

        if assignment.requires_file_submission and not file_submission:
            return JsonResponse(
                {"error": _("File submission is required for this assignment.")},
                status=400,
            )

        file_path = None
        if file_submission:
            file_path = AssignmentSubmission.save_file(
                file_path=file_submission,
                delivery=delivery,
            )

        submission, created = AssignmentSubmission.objects.update_or_create(
            delivery=delivery,
            defaults={
                "file_submission": file_path if file_submission else None,
                "text_submission": text_submission if text_submission else None,
            },
        )
        delivery.reminder_state = ContentDelivery.ReminderStatus.NOT_APPLICABLE
        delivery.valid_until = None
        delivery.remind_at = None
        delivery.save()
        if not created:
            submission.status = AssignmentSubmission.SubmissionStatus.PENDING_REVIEW
            submission.save()

        metric_service.assignment_submitted(
            course_slug=enrollment.course.slug,
            organization_id=enrollment.course.organization.id,
            assignment_id=assignment.id,
        )

        return JsonResponse(
            {
                "message": _("Your assignment submission has been recorded."),
                "status": submission.status,
            },
            status=200,
        )


class QuizSubmissionView(View):
    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = QuizSubmissionRequest.model_validate(payload)
        except ValidationError as ve:
            return JsonResponse({"error": ve.errors()}, status=400)

        token = serializer.token
        answers = serializer.answers

        response_payload, error_response = self.process_quiz_submission(
            token=token,
            answers=answers,
        )
        if error_response:
            return error_response

        return JsonResponse(response_payload, status=200)

    @classmethod
    def process_quiz_submission(
        cls, token: str, answers: list[QuestionResponse]
    ) -> tuple[dict | None, JsonResponse | None]:
        submitted_question_ids = {response.id for response in answers}
        response_map = {response.id: response.answers for response in answers}

        try:
            decoded = jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as jde:
            error_reference = uuid.uuid4()
            logger.warning(f"Invalid token error: {str(jde)} (error_id: {error_reference})")
            return None, JsonResponse({"error": "Invalid token", "error_id": str(error_reference)}, status=400)
        except jwt_service.ExpiredTokenException as ete:
            error_reference = uuid.uuid4()
            logger.warning(f"Expired token error: {str(ete)} (error_id: {error_reference})")
            return None, JsonResponse({"error": "Token is expired", "error_id": str(error_reference)}, status=410)

        delivery_id = decoded["delivery_id"]

        try:
            delivery = ContentDelivery.objects.get(id=delivery_id, hash_value=decoded["delivery_hash"])
        except ContentDelivery.DoesNotExist:
            logger.error(f"Quiz submission failed: No content delivery found for ID {delivery_id} with provided hash.")
            return None, JsonResponse(
                {"error": "The content delivery associated with this token does not exist."},
                status=422,
            )

        enrollment = delivery.enrollment
        if enrollment.status != EnrollmentStatus.ACTIVE:
            return None, JsonResponse({"error": "Quiz is not valid anymore"}, status=400)

        quiz = delivery.course_content.quiz
        if not quiz:
            logger.error(f"Quiz submission failed: No quiz found for content delivery ID {delivery_id}.")
            return None, JsonResponse({"error": "No quiz associated with this link"}, status=422)

        try:
            score, passed = cls.calculate_score_and_passed(quiz, answers, decoded.get("question_ids"))
            logger.info(
                f"Learner ID {enrollment.learner.id} submitted quiz for Course"
                f" {enrollment.course.title} with score {score}. Passed: {passed}"
            )
        except ValueError as ve:
            logger.error(
                f"Quiz submission failed: Error calculating score for content delivery ID {delivery_id}. Error: {ve}"
            )
            return None, JsonResponse({"error": str(ve)}, status=422)

        QuizSubmission.objects.create(
            delivery=delivery,
            score=score,
            is_passed=passed,
        )
        delivery.reminder_state = ContentDelivery.ReminderStatus.NOT_APPLICABLE

        if passed or not quiz.is_blocking:
            delivery.valid_until = None  # Invalidate the quiz link immediately after passing
            delivery.save()
            if quiz.is_blocking:
                delivery.update_hash()  # Invalidate the quiz link after successful submission
                message = _("Congratulations! You have passed the quiz.")
            else:
                message = _("Your quiz submission has been recorded.")
                if QuizSubmission.objects.filter(delivery=delivery).count() >= 10:
                    delivery.update_hash()  # Invalidate the quiz link after 10 attempts to prevent abuse

            if (quiz.is_blocking and passed) or QuizSubmission.objects.filter(delivery=delivery).count() == 1:
                new_delivery = delivery.schedule_next_delivery()

                if not new_delivery:
                    enrollment.graduate()
        else:
            failed_submissions_count = QuizSubmission.objects.filter(
                delivery=delivery,
                is_passed=False,
            ).count()

            if quiz.limited_attempts:
                delivery.update_hash()
                # Check if it's the second attempt failing

                if failed_submissions_count > 1:
                    message = _(
                        "You have failed the quiz twice. Unfortunately, you cannot continue this course"
                        " with this enrollment. You can enroll again to retake the course."
                    )
                    logger.info(
                        f"Learner ID {enrollment.learner.id} has failed the quiz twice"
                        f" for Course {enrollment.course.title}. Marking enrollment as failed."
                    )
                    delivery.remind_at = None
                    delivery.reminder_state = ContentDelivery.ReminderStatus.NOT_APPLICABLE
                    delivery.valid_until = None
                    delivery.save()
                    enrollment.fail()
                else:
                    message = _("You have failed the quiz. You will receive another chance to retake it tomorrow.")
                    logger.info(
                        f"Learner ID {enrollment.learner.id} has failed the quiz for Course {enrollment.course.title}. "
                        f"Scheduling a retry for the next day."
                    )
                    delivery.remind_at = delivery.calculate_remind_at()
                    delivery.valid_until = delivery.calculate_valid_until()
                    delivery.save()
                    delivery.repeat_delivery_in_days(1)
            else:
                delivery.reminder_state = ContentDelivery.ReminderStatus.NOT_APPLICABLE
                delivery.valid_until = None
                delivery.remind_at = None
                delivery.save()
                message = _(f"You have failed the quiz with score {score}. Please review the material and try again.")

        metric_service.quiz_submitted(
            course_slug=enrollment.course.slug,
            organization_id=enrollment.course.organization.id,
            quiz_id=quiz.id,
            is_passed=passed,
            is_blocking=quiz.is_blocking,
        )
        return (
            {
                "score": score,
                "passed": passed,
                "required_score": quiz.required_score,
                "message": message,
                "is_invalidated": quiz.limited_attempts and not passed,
                "is_blocking": quiz.is_blocking,
                "quiz_data": {
                    "id": quiz.id,
                    "title": quiz.title,
                    "questions": [
                        {
                            "text": question.text,
                            "answers": [
                                {
                                    "text": answer.text,
                                    "is_correct": answer.is_correct,
                                    "user_selected": answer.id in response_map.get(question.id, set()),
                                }
                                for answer in question.answers.all()
                            ],
                        }
                        for question in quiz.questions.filter(id__in=submitted_question_ids)
                    ],
                }
                if not quiz.is_blocking
                else None,
            },
            None,
        )

    @staticmethod
    def calculate_score_and_passed(
        quiz: Quiz, answers: list[QuestionResponse], question_ids: list | None
    ) -> tuple[int, bool]:
        # Optimize: Prefetch related answers to avoid N+1 queries
        questions = quiz.questions.prefetch_related("answers").all()

        if question_ids is None:
            question_ids = list(questions.values_list("id", flat=True))

        # Create lookup dictionaries for O(1) access
        questions_dict = {q.id: q for q in questions}
        answers_dict = {}
        correct_answers_count = {}

        # Pre-populate answer lookup and count correct answers per question
        for question_obj in questions:
            answers_dict[question_obj.id] = {a.id: a for a in question_obj.answers.all()}
            correct_answers_count[question_obj.id] = question_obj.answers.filter(is_correct=True).count()

        base_score = 0.0

        for response in answers:
            if response.id not in question_ids:
                raise ValueError(f"Question ID {response.id} is not valid for this quiz.")

            question = questions_dict.get(response.id)
            if not question:
                raise ValueError(f"Question ID {response.id} not found.")

            for answer_id in response.answers:
                # Check if answer exists for this question
                if answer_id not in answers_dict[response.id]:
                    raise ValueError(f"Answer ID {answer_id} is not valid for Question ID {response.id}.")

                answer = answers_dict[response.id][answer_id]
                correct_count = correct_answers_count[response.id]

                if answer.is_correct:
                    base_score += 1 / correct_count  # Full point for correct answer
                else:
                    base_score -= 0.5 / correct_count  # Penalty for incorrect answer

        score = round(base_score / len(question_ids) * 100)  # Score as percentage
        score = max(0, score)
        passed = score >= quiz.required_score
        return score, passed


@method_decorator(csrf_exempt, name="dispatch")
class AmpQuizSubmissionView(View):
    @staticmethod
    def _set_amp_headers(response: JsonResponse, source_origin: str, request_origin: str) -> JsonResponse:
        response["AMP-Email-Allow-Sender"] = source_origin
        response["Access-Control-Allow-Origin"] = request_origin
        response["AMP-Access-Control-Allow-Source-Origin"] = source_origin
        response["Access-Control-Expose-Headers"] = "AMP-Access-Control-Allow-Source-Origin"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    def _amp_json_response(self, payload: dict, status: int, source_origin: str, request_origin: str) -> JsonResponse:
        response = JsonResponse(payload, status=status)
        return self._set_amp_headers(
            response=response,
            source_origin=source_origin,
            request_origin=request_origin,
        )

    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        source_origin = request.GET.get("__amp_source_origin") or request.headers.get("AMP-Email-Sender")
        if not source_origin or not _is_trusted_amp_sender(urllib.parse.unquote(source_origin)):
            return JsonResponse(
                {"error": _("Missing or untrusted __amp_source_origin query parameter.")},
                status=400,
            )

        trusted_origins = {trusted_origin.rstrip("/") for trusted_origin in settings.CSRF_TRUSTED_ORIGINS}
        request_origin = (
            request.headers.get("Origin")
            or request.headers.get("X-Forwarded-Host")
            or request.headers.get("Referer", "").split("/")[0:3]
            and "/".join(request.headers.get("Referer", "").split("/")[:3])
            or None
        )
        if not request_origin:
            return JsonResponse(
                {"error": _("Missing HTTP_ORIGIN header.")},
                status=400,
            )
        normalized_origin = request_origin.rstrip("/")
        if normalized_origin not in trusted_origins:
            return JsonResponse(
                {"error": _("Invalid origin. Untrusted source.")},
                status=400,
            )

        token = request.POST.get("token")
        if not token:
            return self._amp_json_response(
                {"error": _("Token is required.")},
                status=400,
                source_origin=source_origin,
                request_origin=normalized_origin,
            )

        answers_map: dict[int, set[int]] = {}

        for key, values in request.POST.lists():
            if key == "token":
                continue

            try:
                question_id = int(key)
            except (TypeError, ValueError):
                return self._amp_json_response(
                    {"error": _("Invalid question ID in form payload.")},
                    status=400,
                    source_origin=source_origin,
                    request_origin=normalized_origin,
                )

            parsed_answers: set[int] = set()
            for value in values:
                if value in (None, ""):
                    continue

                try:
                    parsed_answers.add(int(value))
                except (TypeError, ValueError):
                    return self._amp_json_response(
                        {"error": _("Invalid answer ID in form payload.")},
                        status=400,
                        source_origin=source_origin,
                        request_origin=normalized_origin,
                    )

            answers_map[question_id] = parsed_answers

        answers = [
            QuestionResponse(id=question_id, answers=answer_ids) for question_id, answer_ids in answers_map.items()
        ]

        response_payload, error_response = QuizSubmissionView.process_quiz_submission(
            token=token,
            answers=answers,
        )
        if error_response:
            return self._set_amp_headers(
                response=error_response,
                source_origin=source_origin,
                request_origin=normalized_origin,
            )

        return self._amp_json_response(
            response_payload,
            status=200,
            source_origin=source_origin,
            request_origin=normalized_origin,
        )


class SubmitCertificateFormView(View):
    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        token = payload.get("token")
        name = payload.get("name")

        if not name:
            return JsonResponse({"error": _("Name is required")}, status=400)
        name = strip_html(name)
        if not name:
            return JsonResponse({"error": _("Name is required")}, status=400)

        try:
            decoded = jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as jde:
            error_reference = uuid.uuid4()
            logger.warning(f"Invalid token error: {str(jde)} (error_id: {error_reference})")
            return JsonResponse({"error": "Invalid token", "error_id": str(error_reference)}, status=400)
        except jwt_service.ExpiredTokenException as ete:
            error_reference = uuid.uuid4()
            logger.warning(f"Expired token error: {str(ete)} (error_id: {error_reference})")
            return JsonResponse({"error": "Token is expired", "error_id": str(error_reference)}, status=410)

        enrollment_id = decoded["enrollment_id"]

        try:
            enrollment = Enrollment.objects.get(id=enrollment_id)
        except Enrollment.DoesNotExist:
            logger.error(f"Certificate generation failed: No enrollment found for ID {enrollment_id}.")
            return JsonResponse(
                {"error": "The enrollment associated with this token does not exist."},
                status=422,
            )

        if enrollment.status != EnrollmentStatus.COMPLETED:
            logger.error(f"Certificate generation failed: Enrollment ID {enrollment_id} is not completed.")
            return JsonResponse(
                {"error": "The enrollment is not completed. Certificate cannot be issued."},
                status=422,
            )
        certificate, created = Certificate.objects.get_or_create(
            enrollment=enrollment, defaults={"name_on_certificate": name}
        )
        certificate_path = reverse(
            "django_email_learning:personalised:certificate",
            kwargs={"certificate_number": certificate.certificate_number},
        )
        absolute_certificate_url = request.build_absolute_uri(certificate_path)

        return JsonResponse({"certificate_url": absolute_certificate_url}, status=200)
