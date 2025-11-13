import pytest
from django_email_learning.models import CourseContent
from django.forms import ValidationError


def test_no_lesson_for_content_of_type_lesson_raises_error(course):
    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=1, type="lesson")


def test_no_quiz_for_content_of_type_quiz_raises_error(course):
    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=1, type="quiz")


def test_lesson_content_for_content_of_type_quiz_raises_error(course, lesson):
    with pytest.raises(ValidationError):
        CourseContent.objects.create(
            course=course, priority=1, type="quiz", lesson=lesson
        )


def test_quiz_content_for_content_of_type_lesson_raises_error(course, quiz):
    with pytest.raises(ValidationError):
        CourseContent.objects.create(
            course=course, priority=1, type="lesson", quiz=quiz
        )


def test_valid_lesson_content_creation(course, lesson):
    content = CourseContent.objects.create(
        course=course, priority=1, type="lesson", lesson=lesson
    )
    assert content.id is not None
    assert content.course == course
    assert content.priority == 1
    assert content.type == "lesson"
    assert content.lesson == lesson
    assert content.quiz is None


def test_valid_quiz_content_creation(course, quiz):
    content = CourseContent.objects.create(
        course=course, priority=1, type="quiz", quiz=quiz
    )
    assert content.id is not None
    assert content.course == course
    assert content.priority == 1
    assert content.type == "quiz"
    assert content.quiz == quiz
    assert content.lesson is None
