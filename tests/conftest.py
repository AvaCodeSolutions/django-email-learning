from django.contrib.auth.models import User
from django_email_learning.models import OrganizationUser
from django.test import Client
from django_email_learning.models import (
    ImapConnection,
    Quiz,
    Lesson,
    Course,
    BlockedEmail,
    Learner,
    Enrollment,
    CourseContent,
    Question,
    Answer,
    EnrollmentStatus,
    ContentDelivery,
    DeliverySchedule,
)
import pytest


@pytest.fixture()
def users(db):
    superadmin = User(
        id=1,
        username="superadmin",
        email="admin@example.com",
        password="adminpass",
        is_superuser=True,
    )
    editor_user = User(
        id=2, username="editor", email="editor@example.com", password="editorpass"
    )
    platform_admin = User(
        id=3,
        username="platformadmin",
        email="platformadmin@example.com",
        password="platformadminpass",
    )
    viewer_user = User(
        id=4, username="viewer", email="viewer@example.com", password="viewerpass"
    )
    User.objects.bulk_create([superadmin, editor_user, platform_admin, viewer_user])
    editor = OrganizationUser(user=editor_user, organization_id=1, role="editor")
    admin = OrganizationUser(user=platform_admin, organization_id=1, role="admin")
    viewer = OrganizationUser(user=viewer_user, organization_id=1, role="viewer")
    OrganizationUser.objects.bulk_create([editor, admin, viewer])
    return {
        "superadmin": superadmin,
        "editor_user": editor_user,
        "platform_admin": platform_admin,
        "viewer_user": viewer_user,
    }


@pytest.fixture(scope="session")
def anonymous_client():
    return Client()


@pytest.fixture()
def superadmin_client(users):
    client = Client()
    client.force_login(users["superadmin"])
    return client


@pytest.fixture()
def editor_client(users):
    client = Client()
    client.force_login(users["editor_user"])
    return client


@pytest.fixture()
def platform_admin_client(users):
    client = Client()
    client.force_login(users["platform_admin"])
    return client


@pytest.fixture()
def viewer_client(users):
    client = Client()
    client.force_login(users["viewer_user"])
    return client


@pytest.fixture()
def client(
    request,
    superadmin_client,
    editor_client,
    platform_admin_client,
    viewer_client,
    anonymous_client,
):
    def _get_client(role_name):
        role_map = {
            "anonymous": anonymous_client,
            "superadmin": superadmin_client,
            "editor": editor_client,
            "platform_admin": platform_admin_client,
            "viewer": viewer_client,
        }
        return role_map.get(role_name)

    return _get_client(request.param)


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
    lesson = Lesson(title="Sample Lesson", content="Lesson Content")
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
        course=course,
        priority=1,
        type="lesson",
        lesson=lesson,
        waiting_period=3600,
        is_published=True,
    )
    return content


@pytest.fixture
def course_quiz_content(db, course, quiz) -> CourseContent:
    content = CourseContent.objects.create(
        course=course, priority=2, type="quiz", quiz=quiz, waiting_period=3600
    )
    return content


@pytest.fixture
def quiz_with_questions(db, quiz) -> Quiz:
    questions = []
    question = Question.objects.create(
        quiz=quiz,
        text="Question?",
        priority=1,
    )
    for i in range(4):
        Answer.objects.create(
            question=question,
            text=f"Answer {i+1}",
            is_correct=(i == 0),  # First answer is correct
        )
    questions.append(question)
    quiz.save()
    return quiz


@pytest.fixture
def active_enrollment(db, learner, course):
    enrollment = Enrollment.objects.create(
        learner=learner, course=course, status=EnrollmentStatus.ACTIVE
    )
    return enrollment


@pytest.fixture
def content_delivery(db, active_enrollment, course_quiz_content, quiz_with_questions):
    course_quiz_content.quiz = quiz_with_questions
    course_quiz_content.is_published = True
    course_quiz_content.save()

    delivery = ContentDelivery.objects.create(
        enrollment=active_enrollment,
        course_content_id=course_quiz_content.id,
        hash_value="testhash",
    )
    delivery.delivery_schedules.add(
        DeliverySchedule.objects.create(is_delivered=True, delivery=delivery)
    )
    return delivery
