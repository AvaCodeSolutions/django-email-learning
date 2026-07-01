from abc import abstractmethod

from pydantic import BaseModel

from django_email_learning.oauth_integrations.base_handler import BaseOAuthSessionHandler


class Group(BaseModel):
    id: str
    name: str


class User(BaseModel):
    email: str
    photo_path: str | None = None

    def __hash__(self) -> int:
        return hash(self.email)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.email == other.email


class BaseGroupEnrollmentHandler(BaseOAuthSessionHandler):
    course_id: int

    @abstractmethod
    def get_groups(self) -> list[Group] | None:
        """
        List the groups that exists in an organization. If the external system does not have a concept of groups,
        return None.
        """
        raise NotImplementedError("Subclasses must implement the get_groups method")

    @abstractmethod
    def get_users_to_enroll(self, groups: set[str]) -> set[User]:
        """
        Enrolls the users in the specified course based on the groups they belong to.
        If groups is None, enroll all users.
        """
        raise NotImplementedError("Subclasses must implement the enroll_user method")
