from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator
from typing import Any
from django_email_learning.models import Organization, ImapConnection, InboxFolder


class CreateImapConnectionRequest(BaseModel):
    email: str = Field(min_length=1, examples=["user@example.com"])
    password: str = Field(min_length=1, examples=["aSafePassword123!"])
    server: str = Field(min_length=1, examples=["imap.example.com"])
    port: int = Field(gt=0, examples=[993])
    folders: list[str] = Field(min_length=1, examples=[["inbox"]])

    @field_validator("folders", mode="after")
    def validate_folders(cls, v: list[str]) -> list[str]:
        if "inbox" not in v:
            raise ValueError("Folders list must contain 'inbox'.")
        return v

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
        imap_connection.save()
        for folder in self.folders:
            InboxFolder.objects.create(
                imap_connection=imap_connection, folder_name=folder
            )
        return imap_connection


class ImapConnectionResponse(BaseModel):
    id: int
    email: str
    server: str
    port: int
    organization_id: int
    folders: Any

    @field_serializer("folders")
    def serialize_folders(self, folders: Any) -> list[str]:
        return [folder.folder_name for folder in folders.all()]  # type: ignore[attr-defined]

    model_config = ConfigDict(from_attributes=True)


class GroupEnrollmentRequest(BaseModel):
    groups: list[str] = Field(
        min_length=1, default=["all"], examples=[["group1", "group2"]]
    )
