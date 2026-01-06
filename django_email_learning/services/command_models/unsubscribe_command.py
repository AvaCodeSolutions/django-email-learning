from typing import Literal
from django_email_learning.services.command_models.abstract_command import (
    AbstractCommand,
)


class UnsubscribeCommand(AbstractCommand):
    command_name: Literal["unsubscribe"]
    email: str
    course_slug: str
    organization_id: int

    def execute(self) -> None:
        print(
            f"Unsubscribing {self.email} from course {self.course_slug} for organization {self.organization_id}"
        )
