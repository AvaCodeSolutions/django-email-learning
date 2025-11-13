from django_email_learning.models import ImapConnection, Quiz, Lesson, Course
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
