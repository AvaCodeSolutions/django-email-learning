import pytest
from django.forms import ValidationError

from django_email_learning.models import ContentDelivery, CourseContent


def test_no_lesson_for_content_of_type_lesson_raises_error(course):
    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=1, type="lesson", waiting_period=10)


def test_no_quiz_for_content_of_type_quiz_raises_error(course):
    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=1, type="quiz", waiting_period=10)


def test_lesson_content_for_content_of_type_quiz_raises_error(course, lesson):
    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=1, type="quiz", lesson=lesson, waiting_period=10)


def test_quiz_content_for_content_of_type_lesson_raises_error(course, quiz):
    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=1, type="lesson", quiz=quiz, waiting_period=10)


def test_valid_lesson_content_creation(course, lesson):
    content = CourseContent.objects.create(course=course, priority=1, type="lesson", lesson=lesson, waiting_period=10)
    assert content.id is not None
    assert content.course == course
    assert content.priority == 1
    assert content.type == "lesson"
    assert content.lesson == lesson
    assert content.quiz is None
    assert content.waiting_period == 10


def test_valid_quiz_content_creation(course, quiz):
    content = CourseContent.objects.create(course=course, priority=1, type="quiz", quiz=quiz, waiting_period=10)
    assert content.id is not None
    assert content.course == course
    assert content.priority == 1
    assert content.type == "quiz"
    assert content.quiz == quiz
    assert content.lesson is None
    assert content.waiting_period == 10


def test_unique_lesson_content_per_course(course, lesson):
    CourseContent.objects.create(course=course, priority=1, type="lesson", lesson=lesson, waiting_period=10)
    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=2, type="lesson", lesson=lesson, waiting_period=20)


def test_unique_quiz_content_per_course(course, quiz):
    CourseContent.objects.create(course=course, priority=1, type="quiz", quiz=quiz, waiting_period=10)
    with pytest.raises(ValidationError):
        CourseContent.objects.create(course=course, priority=2, type="quiz", quiz=quiz, waiting_period=20)


def test_delete_content_without_deliveries_succeeds(course, lesson):
    content = CourseContent.objects.create(course=course, priority=1, type="lesson", lesson=lesson, waiting_period=10)
    content_id = content.id

    content.delete()

    assert not CourseContent.objects.filter(id=content_id).exists()


def test_delete_content_with_a_delivery_is_refused(course_lesson_content, enrollment):
    ContentDelivery.objects.create(enrollment=enrollment, course_content=course_lesson_content)

    with pytest.raises(ValidationError, match="already been scheduled or delivered"):
        course_lesson_content.delete()

    assert CourseContent.objects.filter(id=course_lesson_content.id).exists()
