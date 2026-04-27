from abc import abstractmethod, ABC
from pydantic import BaseModel


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


class BaseGroupEnrollmentHandler(ABC, BaseModel):
    provider_and_purpose: str
    course_id: int
    state: str | None = None
    code: str | None = None

    @abstractmethod
    def handle_redirect(self) -> str:
        """
        Handles the OAuth redirect and returns the access_token
        """
        raise NotImplementedError(
            "Subclasses must implement the handle_redirect method"
        )

    @abstractmethod
    def get_authorization_url(self, state: str) -> str:
        """
        Returns the authorization URL to redirect the user to for OAuth authentication
        """
        raise NotImplementedError(
            "Subclasses must implement the get_authorization_url method"
        )

    @abstractmethod
    def get_groups(self) -> list[Group] | None:
        """
        List the groups that exists in an organization. If the external system does not have a concept of groups, return None.
        """
        raise NotImplementedError("Subclasses must implement the get_groups method")

    @abstractmethod
    def get_users_to_enroll(self, groups: set[str]) -> set[User]:
        """
        Enrolls the users in the specified course based on the groups they belong to. If groups is None, enroll all users.
        """
        raise NotImplementedError("Subclasses must implement the enroll_user method")
