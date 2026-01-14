from pydantic import BaseModel, field_serializer


class PublicCourseSerializer(BaseModel):
    id: int
    title: str
    slug: str
    description: str | None = None
    imap_email: str | None = None

    @field_serializer("description")
    def serialize_description_with_br(self, description: str | None) -> str | None:
        if description is not None:
            return description.replace("\n", "<br />")
        return description


class OrganizationSerializer(BaseModel):
    id: int
    name: str
    logo_url: str | None = None
    description: str | None = None
    courses: list[PublicCourseSerializer] = []

    @field_serializer("description")
    def serialize_description_with_br(self, description: str | None) -> str | None:
        if description is not None:
            return description.replace("\n", "<br>")
        return description
