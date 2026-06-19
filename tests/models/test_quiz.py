from django_email_learning.models import Quiz, Question, Answer
import pytest


def quiz_with_n_questions(n) -> Quiz:
    quiz = Quiz.objects.create(
        title="Sample Quiz",
        required_score=70,
        deadline_days=7,
        selection_strategy="random",
    )
    for i in range(n):
        Question.objects.create(
            quiz=quiz,
            text=f"Question {i + 1}",
            priority=i + 1,
        )
        for j in range(4):
            Answer.objects.create(
                question=quiz.questions.last(),
                text=f"Answer {j + 1} for Question {i + 1}",
                is_correct=(j == 1),
            )
    return quiz


@pytest.mark.parametrize("params", [(3, 3), (20, 13), (6, 5)])
def test_random_question_ids(params, db):
    quiz = quiz_with_n_questions(params[0])
    question_ids = quiz.random_question_ids()
    assert len(question_ids) == params[1]
    assert all(isinstance(q_id, int) for q_id in question_ids)
