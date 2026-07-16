import enum
import re
from typing import Any, Callable, Optional

from django.urls import reverse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from django_email_learning.models import Organization, OrganizationUser, SocialLink
from django_email_learning.services.sanitize import strip_html
from django_email_learning.services.storage_tools import (
    FileDoesNotExistError,
    move_file,
)


class GetOrCreateUserRequest(BaseModel):
    email: str = Field(min_length=1, examples=["user@example.com"])
    organization_id: int = Field(gt=0, examples=[1])

    @field_validator("email")
    def validate_email(cls, email: str) -> str:
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email):
            raise ValueError("Invalid email format")
        return email


class UserResponse(BaseModel):
    id: int
    email: str

    model_config = ConfigDict(from_attributes=True)


class SocialLinkRequest(BaseModel):
    platform: str = Field(examples=[SocialLink.Platform.WEBSITE.value])
    url: str = Field(examples=["https://example.com"])

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, value: str) -> str:
        if value not in SocialLink.Platform.values:
            raise ValueError(f"Invalid platform: {value}")
        return value


class SocialLinkResponse(BaseModel):
    platform: str
    url: str

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None
    logo_path: Optional[str] = None
    description: Optional[str] = None
    public_url: str
    social_links: list[SocialLinkResponse] = []
    is_public: bool
    can_enroll_learner: bool

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def from_django_model(organization: Organization, abs_url_builder: Callable) -> "OrganizationResponse":
        url = reverse(
            "django_email_learning:public:organization_view",
            kwargs={"organization_id": organization.id},
        )
        return OrganizationResponse.model_validate(
            {
                "id": organization.id,
                "name": organization.name,
                "logo": abs_url_builder(organization.logo.url) if organization.logo else None,
                "logo_path": organization.logo.name if organization.logo else None,
                "description": organization.description,
                "public_url": abs_url_builder(url),
                "social_links": list(organization.social_links.all()),
                "is_public": organization.is_public,
                "can_enroll_learner": organization.can_enroll_learner(),
            }
        )


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=1, examples=["AvaCode"])
    description: Optional[str] = Field(None, examples=["A description of the organization."])
    logo: Optional[str] = Field(None, examples=["/path/to/logo.png"])
    social_links: list[SocialLinkRequest] = Field(default_factory=list)
    is_public: bool = Field(default=True, examples=[True])

    @field_validator("description")
    @classmethod
    def strip_html_markup(cls, value: Optional[str]) -> Optional[str]:
        return strip_html(value) if value else value

    def to_django_model(self) -> Organization:
        organization = Organization(
            name=self.name,
            description=self.description,
            is_public=self.is_public,
        )
        organization.save()
        organization.refresh_from_db()
        SocialLink.objects.bulk_create(
            SocialLink(organization=organization, platform=link.platform, url=link.url) for link in self.social_links
        )
        if self.logo:
            try:
                allowed_extensions = [".jpg", ".jpeg", ".png", ".svg"]
                if not any(self.logo.lower().endswith(ext) for ext in allowed_extensions):
                    raise ValueError("Logo must be an image file with a valid extension.")
                final_path = move_file(
                    self.logo,
                    f"organization_logos/{organization.id}/{self.logo.split('/')[-1]}",
                )
                organization.logo = final_path
                organization.save()
            except FileDoesNotExistError:
                raise ValueError("Logo file does not exist.")

        return organization


class UpdateOrganizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, min_length=1, examples=["AvaCode"])
    description: Optional[str] = Field(None, examples=["A description of the organization."])
    social_links: Optional[list[SocialLinkRequest]] = None
    logo: Optional[str] = Field(None, examples=["/path/to/logo.png"])
    remove_logo: Optional[bool] = Field(None, examples=[True])
    is_public: Optional[bool] = Field(None, examples=[True])

    @field_validator("description")
    @classmethod
    def strip_html_markup(cls, value: Optional[str]) -> Optional[str]:
        return strip_html(value) if value else value


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    EDITOR = "editor"
    INSTRUCTOR = "instructor"
    VIEWER = "viewer"


class AddOrganizationUserRequest(BaseModel):
    user_id: int = Field(gt=0, examples=[1])
    role: UserRole = Field(min_length=1, examples=[UserRole.ADMIN])
    display_name: Optional[str] = Field(None, examples=["John Doe"])
    photo: Optional[str] = Field(None, examples=["/path/to/photo.png"])

    @model_validator(mode="before")
    def validate_instructor_display_name(cls, values: dict) -> dict:
        role = values.get("role")
        display_name = values.get("display_name")
        if role == UserRole.INSTRUCTOR and not display_name:
            raise ValueError("Instructor role requires a display name.")
        return values


class UpdateOrganizationUserRequest(BaseModel):
    role: UserRole = Field(min_length=1, examples=[UserRole.ADMIN])
    display_name: Optional[str] = Field(None, examples=["John Doe"])
    photo: Optional[str] = Field(None, examples=["/path/to/photo.png"])

    @model_validator(mode="before")
    def validate_instructor_display_name(cls, values: dict) -> dict:
        role = values.get("role")
        display_name = values.get("display_name")
        if role == UserRole.INSTRUCTOR and not display_name:
            raise ValueError("Instructor role requires a display name.")
        return values


class OrganizationUserResponse(BaseModel):
    id: int
    user_id: int
    organization_id: int
    email: str
    role: UserRole
    can_act_as_instructor: bool
    display_name: Optional[str] = None
    photo: Optional[str] = None
    photo_url: Optional[str] = None

    @staticmethod
    def from_django_model(org_user: OrganizationUser, request: Any) -> "OrganizationUserResponse":
        return OrganizationUserResponse(
            id=org_user.id,
            user_id=org_user.user.id,
            organization_id=org_user.organization.id,
            email=org_user.user.email,
            role=UserRole(org_user.role),
            can_act_as_instructor=org_user.can_act_as_instructor(),
            display_name=org_user.display_name,
            photo=org_user.photo.name if org_user.photo else None,
            photo_url=request.build_absolute_uri(org_user.photo.url) if org_user.photo else None,
        )


class UpdateSessionRequest(BaseModel):
    active_organization_id: int = Field(examples=[1])

    model_config = ConfigDict(extra="forbid")


class SessionInfo(BaseModel):
    active_organization_id: int

    @classmethod
    def populate_from_session(cls, session):  # type: ignore[no-untyped-def]
        return super().model_validate({"active_organization_id": session.get("active_organization_id")})
