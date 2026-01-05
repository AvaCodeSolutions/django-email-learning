from django.http import JsonResponse
from django.views import View
from django_email_learning.personalised.api.serializers import (
    QuizSubmissionRequest,
    QuestionResponse,
)
from django_email_learning.services import jwt_service
from django_email_learning.models import (
    ContentDelivery,
    QuizSubmission,
    Quiz,
    EnrollmentStatus,
)
from pydantic import ValidationError
import json
import logging


class QuizSubmissionView(View):
    def post(self, request, *args, **kwargs):  # type: ignore[no-untyped-def]
        payload = json.loads(request.body)
        try:
            serializer = QuizSubmissionRequest.model_validate(payload)
        except ValidationError as ve:
            return JsonResponse({"error": ve.errors()}, status=400)

        token = serializer.token
        answers = serializer.answers

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

        enrolment = delivery.enrollment
        if enrolment.status != EnrollmentStatus.ACTIVE:
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
        except ValueError as ve:
            return JsonResponse({"error": str(ve)}, status=500)

        QuizSubmission.objects.create(
            delivery=delivery,
            score=score,
            is_passed=passed,
        )
        # Updating the ContentDelivery hash value to invalidate the quiz link
        delivery.update_hash()

        if passed:
            # TODO: Update the next content_delivery if the quiz is passed
            pass
        else:
            # TODO: Schedule the second quiz attempt if the quiz is failed
            pass

        return JsonResponse(
            {
                "score": score,
                "passed": passed,
                "required_score": quiz.required_score,
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

            logging.info(
                f"User submitted quiz with id {quiz.id} with base score {base_score}"
            )

        score = round(base_score / len(question_ids) * 100)  # Score as percentage
        score = max(0, score)
        passed = score >= quiz.required_score
        return score, passed
