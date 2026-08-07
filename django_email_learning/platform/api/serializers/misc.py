from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from django_email_learning.models import ApiKey, ApiKeyScope


class ApiKeyResponse(BaseModel):
    """Metadata about a key. Deliberately carries no secret.

    The token is returned exactly once, by `ApiKeyCreatedResponse` at creation
    time. `key_id` identifies the key afterwards — for display, for revoking
    it, and for correlating it with logs.
    """

    id: int
    key_id: str
    name: str
    key_type: str
    organization_id: Optional[int] = None
    scopes: List[str] = Field(default_factory=list)
    created_at: datetime
    created_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    @staticmethod
    def from_django_model(api_key: ApiKey) -> "ApiKeyResponse":
        return ApiKeyResponse.model_validate(
            {
                "id": api_key.id,  # type: ignore[attr-defined]
                "key_id": api_key.key_id,
                "name": api_key.name,
                "key_type": api_key.key_type,
                "organization_id": api_key.organization_id,
                "scopes": api_key.scopes,
                "created_at": api_key.created_at,
                "created_by": api_key.created_by.username if api_key.created_by else None,
                "expires_at": api_key.expires_at,
                "revoked_at": api_key.revoked_at,
                "last_used_at": api_key.last_used_at,
            }
        )

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreatedResponse(ApiKeyResponse):
    """The creation response, and the only place the token is ever readable."""

    token: str

    @staticmethod
    def from_created_key(api_key: ApiKey, token: str) -> "ApiKeyCreatedResponse":
        return ApiKeyCreatedResponse.model_validate(
            {**ApiKeyResponse.from_django_model(api_key).model_dump(), "token": token}
        )


class CreatePlatformApiKeyRequest(BaseModel):
    name: str = Field(default="Platform key", min_length=1, max_length=100)
    expires_at: Optional[datetime] = None


class CreateOrganizationApiKeyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: List[str] = Field(min_length=1)
    expires_at: Optional[datetime] = None

    @field_validator("scopes")
    def validate_scopes(cls, value: List[str]) -> List[str]:
        unknown = set(value) - set(ApiKeyScope.values)
        if unknown:
            raise ValueError(f"Unknown scopes: {', '.join(sorted(unknown))}")
        # Deduplicated so the stored list matches what a caller sees back.
        return sorted(set(value))
