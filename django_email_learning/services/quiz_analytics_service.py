"""Per-question quiz analytics.

Two responsibilities live here:

* ``record_quiz_submission`` - the single write path for a graded quiz. It stores the
  score alongside the detail the grader already had in hand: which questions the learner
  was shown, and which answers they picked. Neither is reconstructable afterwards, so it
  has to be captured at grade time.
* ``build_quiz_analytics`` - the aggregation the platform UI renders.

**Scope.** Analytics are per :class:`~django_email_learning.models.Quiz`, not per
``CourseContent``. ``CourseContent.quiz`` is a plain ``ForeignKey``, so one quiz can be
attached to contents in several courses - ``CourseContent``'s ``unique_quiz_per_course``
constraint rules out reuse *within* a course, but not across them. When that happens the
numbers below merge those courses' audiences; the aggregation reports every sharing content
in ``shared_with`` so the UI can warn, rather than silently splitting or silently merging.

**Attempts.** Only the *first* attempt per delivery feeds the per-question statistics.
Learners get up to ten attempts, and a non-blocking quiz hands back the full answer key
(``is_correct`` for every option) in its submission response - so any attempt after the
first may have been answered with the answers in front of the learner. Counting those
would make a badly-worded question look easy. Later attempts are still stored, and are
reported separately as ``repeat_attempts``.
"""

from collections import defaultdict
from typing import Any, Iterable, Mapping, Optional

from django_email_learning.models import Quiz, QuizSubmission
from django_email_learning.models.deliveries import ContentDelivery

# Below this many first attempts, rates are reported as None and the UI shows raw counts
# only. Percentages over two or three responses invite conclusions the sample cannot carry.
MIN_RESPONSES_FOR_RATES = 5


def resolve_asked_question_ids(quiz: Quiz, token_question_ids: Optional[Iterable[int]]) -> list[int]:
    """The questions this learner was shown.

    A ``random`` quiz pins its subset into the delivery token at send time; an ``all``
    quiz puts nothing there, and the learner saw whatever questions existed then. This
    mirrors the fallback in ``QuizSubmissionView.calculate_score_and_passed`` so the
    recorded denominator is always the one that was graded against.
    """
    if token_question_ids is not None:
        return list(token_question_ids)
    return list(quiz.questions.values_list("id", flat=True))


def record_quiz_submission(
    delivery: ContentDelivery,
    score: int,
    passed: bool,
    responses: Mapping[int, Iterable[int]],
    asked_question_ids: Iterable[int],
) -> QuizSubmission:
    """Write one graded submission, per-question detail included.

    Called from ``QuizSubmissionView.process_quiz_submission``, which is the single grading
    path for both the hosted quiz page and the in-Gmail AMP form.
    """
    return QuizSubmission.objects.create(
        delivery=delivery,
        score=score,
        is_passed=passed,
        asked_question_ids=list(asked_question_ids),
        # JSON object keys are strings; normalise here so reads never have to guess.
        selected_answer_ids={str(question_id): sorted(answers) for question_id, answers in responses.items()},
    )


def _first_attempts(quiz: Quiz) -> tuple[list[QuizSubmission], int, int]:
    """First attempt per delivery, plus the total and repeat-attempt counts.

    ``submitted_at`` alone can tie (``auto_now_add`` at the same instant on a coarse clock),
    so ``id`` breaks the tie deterministically.
    """
    submissions = list(
        QuizSubmission.objects.filter(delivery__course_content__quiz=quiz).order_by("delivery_id", "submitted_at", "id")
    )
    first_by_delivery: dict[int, QuizSubmission] = {}
    for submission in submissions:
        first_by_delivery.setdefault(submission.delivery_id, submission)
    return list(first_by_delivery.values()), len(submissions), len(submissions) - len(first_by_delivery)


def build_quiz_analytics(quiz: Quiz) -> dict[str, Any]:
    """Aggregate per-question statistics for one quiz.

    A question counts as answered correctly when the learner selected *exactly* the set of
    correct options - no partial credit. That differs from the score the learner sees, which
    awards fractions per correct option and deducts for wrong ones; a single unambiguous
    right/wrong verdict is what makes "60% of learners got this wrong" mean anything.
    """
    questions = list(quiz.questions.prefetch_related("answers").order_by("priority", "id"))
    first_attempts, total_submissions, repeat_attempts = _first_attempts(quiz)

    detailed = [submission for submission in first_attempts if submission.asked_question_ids is not None]
    legacy = len(first_attempts) - len(detailed)

    asked_counts: dict[int, int] = defaultdict(int)
    answered_counts: dict[int, int] = defaultdict(int)
    correct_counts: dict[int, int] = defaultdict(int)
    selected_counts: dict[int, int] = defaultdict(int)

    correct_ids_by_question = {
        question.id: {answer.id for answer in question.answers.all() if answer.is_correct} for question in questions
    }

    for submission in detailed:
        responses = submission.question_response_map()
        for question_id in submission.asked_question_ids or []:
            if question_id not in correct_ids_by_question:
                continue  # Question was deleted from the quiz after this learner sat it.
            asked_counts[question_id] += 1
            selected = responses.get(question_id)
            if not selected:
                continue
            answered_counts[question_id] += 1
            for answer_id in selected:
                selected_counts[answer_id] += 1
            if selected == correct_ids_by_question[question_id]:
                correct_counts[question_id] += 1

    def rate(numerator: int, denominator: int) -> Optional[float]:
        if denominator < MIN_RESPONSES_FOR_RATES:
            return None
        return round(numerator / denominator, 4)

    question_stats = []
    for question in questions:
        asked = asked_counts[question.id]
        question_stats.append(
            {
                "id": question.id,
                "text": question.text,
                "is_multiple_choice": question.is_multiple_choice(),
                "asked_count": asked,
                "answered_count": answered_counts[question.id],
                "skipped_count": asked - answered_counts[question.id],
                "correct_count": correct_counts[question.id],
                "correct_rate": rate(correct_counts[question.id], asked),
                "answers": [
                    {
                        "id": answer.id,
                        "text": answer.text,
                        "is_correct": answer.is_correct,
                        "selected_count": selected_counts[answer.id],
                        "selected_rate": rate(selected_counts[answer.id], asked),
                    }
                    for answer in question.answers.all()
                ],
            }
        )

    shared_with = [
        {
            "content_id": content.id,
            "course_id": content.course_id,
            "course_title": content.course.title,
        }
        for content in quiz.coursecontent_set.select_related("course").order_by("course_id", "id")
    ]

    return {
        "quiz_id": quiz.id,
        "quiz_title": quiz.title,
        "selection_strategy": quiz.selection_strategy,
        "basis": "first_attempt",
        "min_responses_for_rates": MIN_RESPONSES_FOR_RATES,
        "total_submissions": total_submissions,
        "repeat_attempts": repeat_attempts,
        "counted_submissions": len(detailed),
        "legacy_submissions": legacy,
        # More than one entry means this quiz is reused across contents and the figures
        # above pool those audiences. Surfaced, deliberately not corrected for.
        "shared_with": shared_with,
        "questions": question_stats,
    }
