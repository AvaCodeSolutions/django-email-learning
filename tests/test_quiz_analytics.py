"""Capture and aggregation for per-question quiz analytics."""

import pytest
from django.urls import reverse

from django_email_learning.models import (
    Answer,
    ContentDelivery,
    Course,
    CourseContent,
    DeliverySchedule,
    DeliveryStatus,
    Enrollment,
    EnrollmentStatus,
    Learner,
    Question,
    QuizSubmission,
)
from django_email_learning.services import jwt_service, quiz_analytics_service

SUBMISSION_URL = reverse("django_email_learning:api_personalised:quiz_submission")
AMP_URL = reverse("django_email_learning:api_personalised:quiz_amp_submission")


@pytest.fixture
def multi_question_quiz(db, quiz_with_questions):
    """The conftest quiz plus a second, multiple-choice question."""
    second = Question.objects.create(quiz=quiz_with_questions, text="Second question?", priority=2)
    for index in range(3):
        Answer.objects.create(question=second, text=f"B{index + 1}", is_correct=index < 2)
    return quiz_with_questions


def _correct_answer_ids(question):
    return sorted(answer.id for answer in question.answers.filter(is_correct=True))


def _token(delivery, question_ids=None):
    payload = {"delivery_id": delivery.id, "delivery_hash": delivery.hash_value}
    if question_ids is not None:
        payload["question_ids"] = question_ids
    return jwt_service.generate_jwt(payload)


def _submit(client, delivery, responses, question_ids=None):
    return client.post(
        SUBMISSION_URL,
        data={
            "token": _token(delivery, question_ids),
            "answers": [{"id": question_id, "answers": answers} for question_id, answers in responses.items()],
        },
        content_type="application/json",
    )


def test_submission_records_asked_questions_and_selected_answers(
    content_delivery, multi_question_quiz, anonymous_client
):
    first, second = multi_question_quiz.questions.order_by("priority")
    chosen = _correct_answer_ids(first)

    response = _submit(anonymous_client, content_delivery, {first.id: chosen}, question_ids=[first.id, second.id])

    assert response.status_code == 200
    submission = QuizSubmission.objects.get()
    assert submission.asked_question_ids == [first.id, second.id]
    assert submission.selected_answer_ids == {str(first.id): chosen}
    # The unanswered question is in the asked set but absent from the responses.
    assert submission.question_response_map() == {first.id: set(chosen)}


def test_asked_questions_fall_back_to_the_whole_quiz_without_a_token_subset(
    content_delivery, multi_question_quiz, anonymous_client
):
    """An 'all questions' delivery puts no question_ids in the token."""
    first = multi_question_quiz.questions.order_by("priority").first()

    _submit(anonymous_client, content_delivery, {first.id: []})

    submission = QuizSubmission.objects.get()
    assert sorted(submission.asked_question_ids) == sorted(multi_question_quiz.questions.values_list("id", flat=True))


def test_amp_submission_records_the_same_detail(content_delivery, multi_question_quiz, anonymous_client, settings):
    """The in-Gmail form grades through the same path, so it must capture the same detail."""
    from django_email_learning.services.email_sender_service import email_sender_service

    first = multi_question_quiz.questions.order_by("priority").first()
    chosen = _correct_answer_ids(first)

    response = anonymous_client.post(
        f"{AMP_URL}?__amp_source_origin={email_sender_service.from_email}",
        data={"token": _token(content_delivery, [first.id]), str(first.id): [str(chosen[0])]},
        HTTP_ORIGIN=settings.CSRF_TRUSTED_ORIGINS[0],
    )

    assert response.status_code == 200
    submission = QuizSubmission.objects.get()
    assert submission.asked_question_ids == [first.id]
    assert submission.selected_answer_ids == {str(first.id): chosen}


def test_analytics_counts_only_the_first_attempt_per_delivery(db, content_delivery, multi_question_quiz):
    """A retake of a non-blocking quiz is answered with the answer key already revealed."""
    first = multi_question_quiz.questions.order_by("priority").first()
    wrong = [answer.id for answer in first.answers.filter(is_correct=False)][:1]

    for selected, passed in ((wrong, False), (_correct_answer_ids(first), True)):
        # A second attempt is only allowed once the quiz has been delivered again.
        content_delivery.delivery_schedules.add(
            DeliverySchedule.objects.create(status=DeliveryStatus.DELIVERED, delivery=content_delivery)
        )
        QuizSubmission.objects.create(
            delivery=content_delivery,
            score=100 if passed else 0,
            is_passed=passed,
            asked_question_ids=[first.id],
            selected_answer_ids={str(first.id): selected},
        )

    analytics = quiz_analytics_service.build_quiz_analytics(multi_question_quiz)

    assert analytics["total_submissions"] == 2
    assert analytics["counted_submissions"] == 1
    assert analytics["repeat_attempts"] == 1
    stats = {question["id"]: question for question in analytics["questions"]}
    # Only the failing first attempt counts, so the later correct retake is not credited.
    assert stats[first.id]["asked_count"] == 1
    assert stats[first.id]["correct_count"] == 0


def test_rates_are_withheld_below_the_sample_threshold(db, multi_question_quiz, content_delivery):
    first = multi_question_quiz.questions.order_by("priority").first()
    QuizSubmission.objects.create(
        delivery=content_delivery,
        score=100,
        is_passed=True,
        asked_question_ids=[first.id],
        selected_answer_ids={str(first.id): _correct_answer_ids(first)},
    )

    analytics = quiz_analytics_service.build_quiz_analytics(multi_question_quiz)
    stats = {question["id"]: question for question in analytics["questions"]}

    assert analytics["min_responses_for_rates"] == quiz_analytics_service.MIN_RESPONSES_FOR_RATES
    assert stats[first.id]["asked_count"] == 1
    assert stats[first.id]["correct_count"] == 1
    assert stats[first.id]["correct_rate"] is None
    assert all(answer["selected_rate"] is None for answer in stats[first.id]["answers"])


def _extra_delivery(course_content, index):
    """A second learner, enrolled and delivered the same quiz content."""
    learner = Learner.objects.create(
        email=f"analytics-{index}@example.com",
        organization_id=course_content.course.organization_id,
    )
    enrollment = Enrollment.objects.create(
        learner=learner, course=course_content.course, status=EnrollmentStatus.ACTIVE
    )
    delivery = ContentDelivery.objects.create(
        enrollment=enrollment,
        course_content=course_content,
        hash_value=f"analytics-hash-{index}",
    )
    delivery.delivery_schedules.add(DeliverySchedule.objects.create(status=DeliveryStatus.DELIVERED, delivery=delivery))
    return delivery


def test_rates_appear_once_enough_learners_have_answered(db, multi_question_quiz, content_delivery):
    first = multi_question_quiz.questions.order_by("priority").first()
    correct = _correct_answer_ids(first)
    wrong = [answer.id for answer in first.answers.filter(is_correct=False)][:1]

    deliveries = [content_delivery] + [_extra_delivery(content_delivery.course_content, index) for index in range(4)]

    for index, delivery in enumerate(deliveries):
        QuizSubmission.objects.create(
            delivery=delivery,
            score=100 if index < 3 else 0,
            is_passed=index < 3,
            asked_question_ids=[first.id],
            selected_answer_ids={str(first.id): correct if index < 3 else wrong},
        )

    analytics = quiz_analytics_service.build_quiz_analytics(multi_question_quiz)
    stats = {question["id"]: question for question in analytics["questions"]}

    assert stats[first.id]["asked_count"] == 5
    assert stats[first.id]["correct_rate"] == 0.6
    selected = {answer["id"]: answer["selected_count"] for answer in stats[first.id]["answers"]}
    assert selected[correct[0]] == 3
    assert selected[wrong[0]] == 2


def test_partially_correct_multiple_choice_does_not_count_as_correct(db, multi_question_quiz, content_delivery):
    """The score is partial-credit; the analytics verdict deliberately is not."""
    second = multi_question_quiz.questions.order_by("priority").last()
    correct = _correct_answer_ids(second)
    assert len(correct) == 2

    QuizSubmission.objects.create(
        delivery=content_delivery,
        score=50,
        is_passed=False,
        asked_question_ids=[second.id],
        selected_answer_ids={str(second.id): correct[:1]},
    )

    analytics = quiz_analytics_service.build_quiz_analytics(multi_question_quiz)
    stats = {question["id"]: question for question in analytics["questions"]}

    assert stats[second.id]["answered_count"] == 1
    assert stats[second.id]["correct_count"] == 0


def test_legacy_rows_are_counted_but_excluded_from_question_statistics(db, multi_question_quiz, content_delivery):
    first = multi_question_quiz.questions.order_by("priority").first()
    QuizSubmission.objects.create(delivery=content_delivery, score=80, is_passed=True)

    analytics = quiz_analytics_service.build_quiz_analytics(multi_question_quiz)
    stats = {question["id"]: question for question in analytics["questions"]}

    assert analytics["total_submissions"] == 1
    assert analytics["legacy_submissions"] == 1
    assert analytics["counted_submissions"] == 0
    assert stats[first.id]["asked_count"] == 0


def test_a_question_deleted_after_being_asked_is_ignored(db, multi_question_quiz, content_delivery):
    first, second = multi_question_quiz.questions.order_by("priority")
    QuizSubmission.objects.create(
        delivery=content_delivery,
        score=100,
        is_passed=True,
        asked_question_ids=[first.id, second.id],
        selected_answer_ids={str(second.id): _correct_answer_ids(second)},
    )
    second_id = second.id
    second.delete()

    analytics = quiz_analytics_service.build_quiz_analytics(multi_question_quiz)

    assert [question["id"] for question in analytics["questions"]] == [first.id]
    assert second_id not in [question["id"] for question in analytics["questions"]]


def test_a_quiz_reused_across_courses_reports_every_course_sharing_it(
    db, multi_question_quiz, course, course_quiz_content, imap_connection
):
    """`unique_quiz_per_course` bars reuse inside one course, so reuse means a second course."""
    other_course = Course.objects.create(
        title="Second Course",
        slug="second-course",
        description="Another course reusing the same quiz.",
        organization_id=course.organization_id,
        imap_connection=imap_connection,
    )
    CourseContent.objects.create(
        course=other_course, priority=1, type="quiz", quiz=multi_question_quiz, waiting_period=60
    )

    analytics = quiz_analytics_service.build_quiz_analytics(multi_question_quiz)

    # Two entries mean the figures pool both courses' audiences - surfaced, not corrected.
    assert {entry["course_id"] for entry in analytics["shared_with"]} == {course.id, other_course.id}


@pytest.mark.parametrize("client_name", ["org_admin_client", "editor_client", "instructor_client", "viewer_client"])
def test_analytics_endpoint_is_readable_by_every_org_role(
    request, client_name, multi_question_quiz, course_quiz_content
):
    client = request.getfixturevalue(client_name)
    url = reverse(
        "django_email_learning:api_platform:quiz_analytics",
        kwargs={"organization_id": course_quiz_content.course.organization_id, "quiz_id": multi_question_quiz.id},
    )

    response = client.get(url)

    assert response.status_code == 200
    assert response.json()["quiz_id"] == multi_question_quiz.id
    assert response.json()["basis"] == "first_attempt"


def test_analytics_endpoint_404s_for_a_quiz_outside_the_organization(
    org_admin_client, multi_question_quiz, course_quiz_content
):
    url = reverse(
        "django_email_learning:api_platform:quiz_analytics",
        kwargs={"organization_id": course_quiz_content.course.organization_id + 999, "quiz_id": multi_question_quiz.id},
    )

    assert org_admin_client.get(url).status_code in (403, 404)
