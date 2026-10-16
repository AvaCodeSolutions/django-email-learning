from enum import StrEnum


class EnrollmentConfirmation(StrEnum):
    """How a course's new enrollments go from unverified to active."""

    # The learner clicks the verification link emailed to them, or replies with its code.
    LINK = "link"
    # Something outside the course - a payment, a signed contract - confirms it through the
    # unlock API naming the course's enrollment gate key, or an admin does.
    GATE = "gate"
