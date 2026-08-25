from enum import StrEnum


class DeactivationReason(StrEnum):
    CANCELED = "canceled"
    BLOCKED = "blocked"
    FAILED = "failed"
    INACTIVE = "inactive"
    REVOKED = "revoked"
