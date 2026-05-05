from django.http import JsonResponse
from django.views import View
from django.urls import reverse
from django.utils import timezone
from django_email_learning.personalised.api.serializers import (
    QuizSubmissionRequest,
    QuestionResponse,
)
from django_email_learning.services.metrics_service import MetricsService
from django_email_learning.services import jwt_service
from django.utils.translation import gettext as _
from django_email_learning.models import (
    AssignmentSubmission,
    ContentDelivery,
    Enrollment,
    Certificate,
    QuizSubmission,
    Quiz,
    EnrollmentStatus,
)
from pydantic import ValidationError
import json
import logging
from django.core.files.storage import default_storage

METRIC_SERVICE = MetricsService()

logger = logging.getLogger(__name__)


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
            return JsonResponse({"error": str(jde)}, status=400)
        except jwt_service.ExpiredTokenException as ete:
            return JsonResponse({"error": str(ete)}, status=410)

        try:
            delivery = ContentDelivery.objects.get(
                id=decoded["delivery_id"],
                hash_value=decoded["delivery_hash"],
            )
        except ContentDelivery.DoesNotExist:
            return JsonResponse(
                {
                    "error": "The content delivery associated with this token does not exist."
                },
                status=500,
            )

        if delivery.enrollment.status != EnrollmentStatus.ACTIVE:
            return JsonResponse(
                {"error": _("File upload is not valid anymore")}, status=400
            )

        date_prefix = timezone.now().strftime("%Y%m%d")
        file_path = default_storage.save(
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
                {
                    "error": _(
                        "At least one of text submission or file submission is required."
                    )
                },
                status=400,
            )

        try:
            decoded = jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as jde:
            return JsonResponse({"error": str(jde)}, status=400)
        except jwt_service.ExpiredTokenException as ete:
            return JsonResponse({"error": str(ete)}, status=410)

        delivery_id = decoded["delivery_id"]
        try:
            delivery = ContentDelivery.objects.get(
                id=delivery_id, hash_value=decoded["delivery_hash"]
            )
        except ContentDelivery.DoesNotExist:
            return JsonResponse(
                {
                    "error": "The content delivery associated with this token does not exist."
                },
                status=500,
            )

        existing_submission = AssignmentSubmission.objects.filter(
            delivery=delivery
        ).first()
        if (
            existing_submission
            and existing_submission.status
            != AssignmentSubmission.SubmissionStatus.REQUESTING_CHANGES
        ):
            return JsonResponse(
                {
                    "error": _(
                        "There is already a submission for this assignment. Please wait for it to be reviewed before submitting again."
                    )
                },
                status=400,
            )

        enrollment = delivery.enrollment
        if enrollment.status != EnrollmentStatus.ACTIVE:
            return JsonResponse(
                {"error": "Assignment submission is not valid anymore"}, status=400
            )

        assignment = delivery.course_content.assignment
        if not assignment:
            return JsonResponse(
                {"error": "No assignment associated with this link"}, status=500
            )

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

        METRIC_SERVICE.assignment_submitted(
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

        submited_question_ids = {response.id for response in answers}
        response_map = {response.id: response.answers for response in answers}

        try:
            decoded = jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as jde:
            return JsonResponse({"error": str(jde)}, status=400)
        except jwt_service.ExpiredTokenException as ete:
            return JsonResponse({"error": str(ete)}, status=410)

        delivery_id = decoded["delivery_id"]

        try:
            delivery = ContentDelivery.objects.get(
                id=delivery_id, hash_value=decoded["delivery_hash"]
            )
        except ContentDelivery.DoesNotExist:
            return JsonResponse(
                {
                    "error": "The content delivery associated with this token does not exist."
                },
                status=500,
            )

        enrollment = delivery.enrollment
        if enrollment.status != EnrollmentStatus.ACTIVE:
            return JsonResponse({"error": "Quiz is not valid anymore"}, status=400)

        quiz = delivery.course_content.quiz
        if not quiz:
            return JsonResponse(
                {"error": "No quiz associated with this link"}, status=500
            )

        try:
            score, passed = self.calculate_score_and_passed(
                quiz, answers, decoded.get("question_ids")
            )
            logger.info(
                f"Learner ID {enrollment.learner.id} submitted quiz for Course {enrollment.course.title} with score {score}. Passed: {passed}"
            )
        except ValueError as ve:
            return JsonResponse({"error": str(ve)}, status=500)

        QuizSubmission.objects.create(
            delivery=delivery,
            score=score,
            is_passed=passed,
        )
        delivery.reminder_state = ContentDelivery.ReminderStatus.NOT_APPLICABLE

        if passed or not quiz.is_blocking:
            delivery.valid_until = (
                None  # Invalidate the quiz link immediately after passing
            )
            delivery.save()
            if quiz.is_blocking:
                delivery.update_hash()  # Invalidate the quiz link after successful submission
                message = _("Congratulations! You have passed the quiz.")
            else:
                message = _("Your quiz submission has been recorded.")
                if QuizSubmission.objects.filter(delivery=delivery).count() >= 10:
                    delivery.update_hash()  # Invalidate the quiz link after 10 attempts to prevent abuse

            if (quiz.is_blocking and passed) or QuizSubmission.objects.filter(
                delivery=delivery
            ).count() == 1:
                delivery = delivery.schedule_next_delivery()

            if not delivery:
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
                        "You have failed the quiz twice. Unfortunately, you cannot continue this course with this enrollment. You can enroll again to retake the course."
                    )
                    logger.info(
                        f"Learner ID {enrollment.learner.id} has failed the quiz twice for Course {enrollment.course.title}. "
                        f"Marking enrollment as failed."
                    )
                    delivery.remind_at = None
                    delivery.reminder_state = (
                        ContentDelivery.ReminderStatus.NOT_APPLICABLE
                    )
                    delivery.valid_until = None
                    delivery.save()
                    enrollment.fail()
                else:
                    message = _(
                        "You have failed the quiz. You will receive another chance to retake it tomorrow."
                    )
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
                message = _(
                    f"You have failed the quiz with score {score}. Please review the material and try again."
                )

        METRIC_SERVICE.quiz_submitted(
            course_slug=enrollment.course.slug,
            organization_id=enrollment.course.organization.id,
            quiz_id=quiz.id,
            is_passed=passed,
            is_blocking=quiz.is_blocking,
        )
        return JsonResponse(
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
                                    "user_selected": answer.id
                                    in response_map.get(question.id, set()),
                                }
                                for answer in question.answers.all()
                            ],
                        }
                        for question in quiz.questions.filter(
                            id__in=submited_question_ids
                        )
                    ],
                }
                if not quiz.is_blocking
                else None,
            },
            status=200,
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
            answers_dict[question_obj.id] = {
                a.id: a for a in question_obj.answers.all()
            }
            correct_answers_count[question_obj.id] = question_obj.answers.filter(
                is_correct=True
            ).count()

        base_score = 0.0

        for response in answers:
            if response.id not in question_ids:
                raise ValueError(
                    f"Question ID {response.id} is not valid for this quiz."
                )

            question = questions_dict.get(response.id)
            if not question:
                raise ValueError(f"Question ID {response.id} not found.")

            for answer_id in response.answers:
                # Check if answer exists for this question
                if answer_id not in answers_dict[response.id]:
                    raise ValueError(
                        f"Answer ID {answer_id} is not valid for Question ID {response.id}."
                    )

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


class SubmitCertificateFormView(View):
    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        token = payload.get("token")
        name = payload.get("name")

        if not name:
            return JsonResponse({"error": _("Name is required")}, status=400)

        try:
            decoded = jwt_service.decode_jwt(token=token)
        except jwt_service.InvalidTokenException as jde:
            return JsonResponse({"error": str(jde)}, status=400)
        except jwt_service.ExpiredTokenException as ete:
            return JsonResponse({"error": str(ete)}, status=410)

        enrollment_id = decoded["enrollment_id"]

        try:
            enrollment = Enrollment.objects.get(id=enrollment_id)
        except Enrollment.DoesNotExist:
            return JsonResponse(
                {"error": "The enrollment associated with this token does not exist."},
                status=500,
            )

        if enrollment.status != EnrollmentStatus.COMPLETED:
            return JsonResponse(
                {
                    "error": "The enrollment is not completed. Certificate cannot be issued."
                },
                status=400,
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
