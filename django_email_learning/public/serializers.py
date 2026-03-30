from pydantic import BaseModel, field_serializer


class PublicCourseSerializer(BaseModel):
    id: int
    title: str
    slug: str
    description: str | None = None
    imap_email: str | None = None
    image: str | None = None
    language: str
    is_rtl: bool = False
    lessons: list[str] = []

    @field_serializer("description")
    def serialize_description_with_br(self, description: str | None) -> str | None:
        if description is not None:
            return description.replace("\n", "<br />")
        return description

    @field_serializer("language")
    def serialize_language(self, language_code: str) -> str:
        from django.conf.global_settings import LANGUAGES

        language_dict = dict(LANGUAGES)
        return language_dict.get(language_code, language_code)


class OrganizationSerializer(BaseModel):
    id: int
    name: str
    logo_url: str | None = None
    description: str | None = None
    courses: list[PublicCourseSerializer] = []
    public_url: str

    @field_serializer("description")
    def serialize_description_with_br(self, description: str | None) -> str | None:
        if description is not None:
            return description.replace("\n", "<br>")
        return description
