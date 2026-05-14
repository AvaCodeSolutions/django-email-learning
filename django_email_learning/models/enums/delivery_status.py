from enum import StrEnum


class DeliveryStatus(StrEnum):
    SCHEDULED = "scheduled"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    CANCELED = "canceled"
    BLOCKED = "blocked"
