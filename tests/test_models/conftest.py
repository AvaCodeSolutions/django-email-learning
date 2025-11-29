from django_email_learning.models import (
    ImapConnection,
    Quiz,
    Lesson,
    Course,
    BlockedEmail,
    Learner,
    Enrollment,
    CourseContent,
)
import pytest


@pytest.fixture()
def imap_connection(db) -> ImapConnection:
    connection = ImapConnection(
        server="IMAP.example.com",
        port=993,
        email="user@example.com",
        password="my_secret_password",
        organization_id=1,
    )
    connection.save()
    return connection


@pytest.fixture()
def quiz(db) -> Quiz:
    quiz = Quiz(title="Sample Quiz", required_score=70)
    quiz.save()
    return quiz


@pytest.fixture()
def lesson(db) -> Lesson:
    lesson = Lesson(title="Sample Lesson", content="Lesson Content", is_published=True)
    lesson.save()
    return lesson


@pytest.fixture()
def course(db, imap_connection) -> Course:
    course = Course(
        title="Sample Course",
        slug="sample-course",
        imap_connection=imap_connection,
        organization_id=1,
    )
    course.save()
    return course


@pytest.fixture()
def blocked_email(db) -> BlockedEmail:
    blocked_email = BlockedEmail(email="blacklisted@email.com")
    blocked_email.save()
    return blocked_email


@pytest.fixture()
def learner(db) -> Learner:
    learner = Learner(email="user@example.com")
    learner.save()
    return learner


@pytest.fixture()
def enrollment(db, learner, course) -> Enrollment:
    enrollment = Enrollment.objects.create(learner=learner, course=course)
    return enrollment


@pytest.fixture
def course_lesson_content(db, course, lesson) -> CourseContent:
    content = CourseContent.objects.create(
        course=course, priority=1, type="lesson", lesson=lesson, waiting_period=10
    )
    return content


@pytest.fixture
def course_quiz_content(db, course, quiz) -> CourseContent:
    content = CourseContent.objects.create(
        course=course, priority=2, type="quiz", quiz=quiz, waiting_period=5
    )
    return content
