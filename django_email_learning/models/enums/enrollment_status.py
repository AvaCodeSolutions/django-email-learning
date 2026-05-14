from enum import StrEnum


class EnrollmentStatus(StrEnum):
    UNVERIFIED = "unverified"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEACTIVATED = "deactivated"
