from typing import Literal

from pydantic import Field

from django_email_learning.models import (
    Enrollment,
    EnrollmentStatus,
)
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)
from django_email_learning.services.command_models.exceptions.invalid_enrollment_error import (
    InvalidEnrollmentError,
)
from django_email_learning.services.command_models.exceptions.invalid_verification_code_error import (
    InvalidVerificationCodeError,
)
from django_email_learning.services.enrollment_confirmation_service import activate_enrollment
from django_email_learning.services.enrollment_emails import send_welcome_email


class VerifyEnrollmentCommand(AbstractCommand):
    command_name: Literal["verify_enrollment"] = "verify_enrollment"
    enrollment_id: int = Field(..., gt=0)
    verification_code: str = Field(..., pattern=r"^\d{6}$")
    # A course with gated enrollments is confirmed through its gate, never by the learner.
    # Trusted callers that activate an enrollment directly - an admin enrolling someone,
    # an API key enrolling a learner already verified - set this to pass the gate.
    skip_enrollment_gate: bool = False

    def execute(self) -> None:
        try:
            enrollment = Enrollment.objects.get(id=self.enrollment_id, status=EnrollmentStatus.UNVERIFIED)
        except Enrollment.DoesNotExist:
            self.logger.error(f"Verification Failed: No unverified enrollment found with ID {self.enrollment_id}")
            # Check if enrollment exists but is not unverified
            if Enrollment.objects.filter(id=self.enrollment_id).exists():
                return
            raise InvalidEnrollmentError(f"No unverified enrollment found with ID {self.enrollment_id}")

        if str(enrollment.activation_code) != str(self.verification_code):
            self.logger.error(f"Verification Failed: Invalid verification code for Enrollment ID {self.enrollment_id}")
            raise InvalidVerificationCodeError(f"Invalid verification code for Enrollment ID {self.enrollment_id}")

        if enrollment.course.is_enrollment_gated and not self.skip_enrollment_gate:
            self.logger.error(f"Verification Failed: Enrollment ID {self.enrollment_id} is confirmed through its gate")
            raise InvalidEnrollmentError(f"Enrollment {self.enrollment_id} must be confirmed through its gate")

        activate_enrollment(enrollment)
        send_welcome_email(enrollment)
