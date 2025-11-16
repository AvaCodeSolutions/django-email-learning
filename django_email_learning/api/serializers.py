from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from django_email_learning.models import Course
from django_email_learning.models import Organization, ImapConnection


class CreateCourseRequest(BaseModel):
    title: str = Field(min_length=1, examples=["Introduction to Python"])
    slug: str = Field(
        min_length=1,
        examples=["intro-to-python"],
        description="A short label for the course, used in URLs or email interactive actions. "
        "You can not edit it later.",
    )
    description: Optional[str] = Field(
        None, examples=["A beginner's course on Python programming."]
    )
    imap_connection_id: Optional[int] = Field(None, examples=[1])

    def to_django_model(self, organization_id: int) -> Course:
        organization = Organization.objects.get(id=organization_id)
        if not organization:
            raise ValueError(f"Organization with id {organization_id} does not exist.")
        imap_connection = None
        if self.imap_connection_id:
            try:
                imap_connection = ImapConnection.objects.get(
                    id=self.imap_connection_id, organization=organization
                )
            except ImapConnection.DoesNotExist:
                raise ValueError(
                    f"ImapConnection with id {self.imap_connection_id} does not exist."
                )
            imap_connection = ImapConnection.objects.get(
                id=self.imap_connection_id, organization=organization
            )
        course = Course(
            title=self.title,
            slug=self.slug,
            description=self.description,
            organization=organization,
        )
        if imap_connection:
            course.imap_connection = imap_connection
        return course


class UpdateCourseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(
        None, min_length=1, examples=["Introduction to Python"]
    )
    description: Optional[str] = Field(
        None, examples=["A beginner's course on Python programming."]
    )
    imap_connection_id: Optional[int] = Field(None, examples=[1])
    enabled: Optional[bool] = Field(None, examples=[True])
    reset_imap_connection: Optional[bool] = Field(None, examples=[False])

    def to_django_model(self, course_id: int) -> Course:
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            raise ValueError(f"Course with id {course_id} does not exist.")
        if self.reset_imap_connection and self.imap_connection_id is not None:
            raise ValueError(
                "Cannot set imap_connection_id when reset_imap_connection is True."
            )

        if self.title is not None:
            course.title = self.title
        if self.description is not None:
            course.description = self.description
        if self.imap_connection_id is not None:
            imap_connection = ImapConnection.objects.get(id=self.imap_connection_id)
            course.imap_connection = imap_connection
        if self.enabled is not None:
            course.enabled = self.enabled
        if self.reset_imap_connection:
            course.imap_connection = None

        return course


class CourseResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str]
    organization_id: int
    imap_connection_id: Optional[int]
    enabled: bool

    model_config = ConfigDict(from_attributes=True)


class CreateImapConnectionRequest(BaseModel):
    email: str = Field(min_length=1, examples=["user@example.com"])
    password: str = Field(min_length=1, examples=["aSafePassword123!"])
    server: str = Field(min_length=1, examples=["imap.example.com"])
    port: int = Field(gt=0, examples=[993])

    def to_django_model(self, organization_id: int) -> ImapConnection:
        organization = Organization.objects.get(id=organization_id)
        if not organization:
            raise ValueError(f"Organization with id {organization_id} does not exist.")
        imap_connection = ImapConnection(
            email=self.email,
            password=self.password,
            server=self.server,
            port=self.port,
            organization=organization,
        )
        return imap_connection


class ImapConnectionResponse(BaseModel):
    id: int
    email: str
    server: str
    port: int
    organization_id: int

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, examples=["AvaCode"])
    description: Optional[str] = Field(
        None, examples=["A description of the organization."]
    )

    def to_django_model(self) -> Organization:
        organization = Organization(name=self.name, description=self.description)
        return organization


class UpdateSessionRequest(BaseModel):
    active_organization_id: int = Field(examples=[1])

    model_config = ConfigDict(extra="forbid")


class SessionInfo(BaseModel):
    active_organization_id: int

    @classmethod
    def populate_from_session(cls, session):  # type: ignore[no-untyped-def]
        return super().model_validate(
            {"active_organization_id": session.get("active_organization_id")}
        )
