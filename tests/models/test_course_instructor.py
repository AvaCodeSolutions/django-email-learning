import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from django_email_learning.models import (
    Course,
    CourseInstructor,
    Organization,
    OrganizationUser,
)


@pytest.fixture
def org_instructor(users) -> OrganizationUser:
    instructor_user = users["instructor_user"]
    instructor = OrganizationUser.objects.get(user=instructor_user)

    return instructor


@pytest.fixture
def org_editor(users) -> OrganizationUser:
    editor_user = users["editor_user"]
    editor = OrganizationUser.objects.get(user=editor_user)

    return editor


@pytest.fixture
def organization() -> Organization:
    return Organization.objects.first()


@pytest.fixture
def org_instructor_different_org() -> OrganizationUser:
    instructor_user = User.objects.create_user(
        username="instructor_different_org",
        email="instructor_different_org@example.com",
        password="password123",
    )
    different_org = Organization.objects.create(name="Different Org")
    instructor = OrganizationUser.objects.create(
        user=instructor_user,
        organization=different_org,
        role="instructor",
        display_name="Instructor Different Org",
    )
    return instructor


class TestCourseInstructorCreation:
    """Test CourseInstructor creation and basic functionality."""

    def test_create_valid_course_instructor(self, db, org_instructor, course):
        """Test creating a valid CourseInstructor."""
        course_instructor = CourseInstructor.objects.create(
            course=course,
            org_user=org_instructor,
        )

        assert course_instructor.id is not None
        assert course_instructor.course == course
        assert course_instructor.org_user == org_instructor

    def test_course_instructor_str_representation(self, db, course, org_instructor):
        """Test the __str__ method returns expected format."""
        course_instructor = CourseInstructor.objects.create(
            course=course,
            org_user=org_instructor,
        )

        expected = f"{course.title} - {org_instructor.user.email}"
        assert str(course_instructor) == expected

    def test_course_instructor_str_with_different_email(self, db, course, org_instructor):
        """Test __str__ method reflects org_user email correctly."""
        course_instructor = CourseInstructor.objects.create(
            course=course,
            org_user=org_instructor,
        )

        assert org_instructor.user.email in str(course_instructor)
        assert course.title in str(course_instructor)


class TestCourseInstructorValidation:
    """Test CourseInstructor validation rules."""

    def test_cannot_add_instructor_from_different_organization(self, db, course, org_instructor_different_org):
        """Test that instructor from different organization cannot be added."""
        with pytest.raises(ValidationError) as exc_info:
            CourseInstructor(
                course=course,
                org_user=org_instructor_different_org,
            ).save()

        assert "Instructor must belong to the same organization as the course." in str(exc_info.value)

    def test_cannot_add_non_instructor_role(self, db, course, org_editor):
        """Test that org_user without instructor role cannot be added."""
        with pytest.raises(ValidationError) as exc_info:
            CourseInstructor(
                course=course,
                org_user=org_editor,
            ).save()

        assert "Organization user doesn't have instructor role." in str(exc_info.value)

    def test_validation_happens_on_save(self, db, course, org_instructor_different_org):
        """Test that validation occurs during save, not instantiation."""
        # Instantiation should work
        course_instructor = CourseInstructor(
            course=course,
            org_user=org_instructor_different_org,
        )
        assert course_instructor is not None

        # Save should fail
        with pytest.raises(ValidationError):
            course_instructor.save()


class TestCourseInstructorUniqueness:
    """Test CourseInstructor uniqueness constraints."""

    def test_unique_constraint_course_org_user(self, db, course, org_instructor):
        """Test that same course-org_user combination is unique."""
        CourseInstructor.objects.create(
            course=course,
            org_user=org_instructor,
        )

        with pytest.raises(ValidationError) as exc_info:
            CourseInstructor.objects.create(
                course=course,
                org_user=org_instructor,
            )
        assert "Course instructor with this Course and Org user already exists." in str(exc_info.value)

    def test_same_instructor_can_teach_multiple_courses(self, db, organization, org_instructor):
        """Test that same instructor can be added to multiple courses."""
        course1 = Course.objects.create(
            title="Course 1",
            slug="course-1",
            organization=organization,
        )
        course2 = Course.objects.create(
            title="Course 2",
            slug="course-2",
            organization=organization,
        )

        instructor1 = CourseInstructor.objects.create(
            course=course1,
            org_user=org_instructor,
        )
        instructor2 = CourseInstructor.objects.create(
            course=course2,
            org_user=org_instructor,
        )

        assert instructor1.id != instructor2.id
        assert instructor1.org_user == instructor2.org_user
        assert instructor1.course != instructor2.course

    def test_different_instructors_can_teach_same_course(self, db, course, organization):
        """Test that multiple instructors can be added to same course."""
        instructor_user2 = User.objects.create_user(
            username="instructor2",
            email="instructor2@example.com",
            password="testpass123",
        )
        org_instructor2 = OrganizationUser.objects.create(
            user=instructor_user2,
            organization=organization,
            role="instructor",
            display_name="Instructor 2",
        )

        instructor_user3 = User.objects.create_user(
            username="instructor3",
            email="instructor3@example.com",
            password="testpass123",
        )
        org_instructor3 = OrganizationUser.objects.create(
            user=instructor_user3,
            organization=organization,
            role="instructor",
            display_name="Instructor 3",
        )

        course_instr1 = CourseInstructor.objects.create(
            course=course,
            org_user=org_instructor2,
        )
        course_instr2 = CourseInstructor.objects.create(
            course=course,
            org_user=org_instructor3,
        )

        assert course_instr1.course == course_instr2.course
        assert course_instr1.org_user != course_instr2.org_user


class TestCourseInstructorRelationships:
    """Test CourseInstructor relationships and related_name."""

    def test_related_name_instructors_on_course(self, db, course, org_instructor):
        """Test accessing instructors through course.instructors related_name."""
        CourseInstructor.objects.create(
            course=course,
            org_user=org_instructor,
        )

        instructors = course.instructors.all()
        assert instructors.count() == 1
        assert instructors.first().org_user == org_instructor

    def test_multiple_instructors_via_related_name(self, db, course, organization):
        """Test accessing multiple instructors through related_name."""
        instructor_user1 = User.objects.create_user(
            username="inst1",
            email="inst1@example.com",
            password="pass123",
        )
        instructor_user2 = User.objects.create_user(
            username="inst2",
            email="inst2@example.com",
            password="pass123",
        )

        org_instructor1 = OrganizationUser.objects.create(
            user=instructor_user1,
            organization=organization,
            role="instructor",
            display_name="Instructor 1",
        )
        org_instructor2 = OrganizationUser.objects.create(
            user=instructor_user2,
            organization=organization,
            role="instructor",
            display_name="Instructor 2",
        )

        CourseInstructor.objects.create(course=course, org_user=org_instructor1)
        CourseInstructor.objects.create(course=course, org_user=org_instructor2)

        instructors = course.instructors.all()
        assert instructors.count() == 2
        assert org_instructor1 in [ci.org_user for ci in instructors]
        assert org_instructor2 in [ci.org_user for ci in instructors]

    def test_delete_course_instructor_cascade(self, db, course, org_instructor):
        """Test that deleting a CourseInstructor works correctly."""
        course_instructor = CourseInstructor.objects.create(
            course=course,
            org_user=org_instructor,
        )
        course_instructor_id = course_instructor.id

        course_instructor.delete()

        assert not CourseInstructor.objects.filter(id=course_instructor_id).exists()
