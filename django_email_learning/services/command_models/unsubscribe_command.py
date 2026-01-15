from typing import Literal
from django_email_learning.models import (
    Course,
    Enrollment,
    Learner,
    EnrollmentStatus,
    DeactivationReason,
)
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.command_models.exceptions.invalid_course_slug_error import (
    InvalidCourseSlugError,
)


class UnsubscribeCommand(AbstractCommand):
    command_name: Literal["unsubscribe"] = "unsubscribe"
    email: str
    course_slug: str
    organization_id: int

    def execute(self) -> None:
        try:
            course = Course.objects.get(
                slug=self.course_slug, organization_id=self.organization_id
            )
        except Course.DoesNotExist:
            self.logger.error(
                f"Unsubscribe Failed: Invalid course slug '{self.course_slug}' for organization ID {self.organization_id}"
            )
            raise InvalidCourseSlugError(
                f"Course with slug '{self.course_slug}' does not exist for organization ID {self.organization_id}"
            )

        try:
            learner = Learner.objects.get(
                email=self.email,
                organization_id=self.organization_id,  # type: ignore[misc]
            )
        except Learner.DoesNotExist:
            self.logger.warning(
                f"Unsubscribe Skipped: No learner found with email {self.email}"
            )
            return

        enrollments = Enrollment.objects.filter(learner=learner, course=course).exclude(
            status=EnrollmentStatus.DEACTIVATED
        )
        if not enrollments.exists():
            self.logger.warning(
                f"Unsubscribe Skipped: No active enrollment found for learner {learner.id} in course {course.slug}"
            )
            return

        enrollments.update(
            status=EnrollmentStatus.DEACTIVATED,
            deactivation_reason=DeactivationReason.CANCELED,
        )
