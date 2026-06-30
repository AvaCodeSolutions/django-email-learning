from datetime import datetime
from typing import Optional

from django.utils import timezone
from pydantic import BaseModel, ConfigDict

from django_email_learning.models import ApiKey
from django_email_learning.services.jwt_service import generate_jwt


class ApiKeyResponse(BaseModel):
    id: int
    key: str
    created_at: datetime
    created_by: Optional[str] = None

    @staticmethod
    def from_django_model(api_key: ApiKey) -> "ApiKeyResponse":
        decrypted_key = api_key.decrypt_password(api_key.key)
        salt = api_key.salt
        jwt_key = generate_jwt(
            {"key": decrypted_key, "salt": salt},
            exp=datetime.max.replace(tzinfo=timezone.get_current_timezone()),
        )

        return ApiKeyResponse.model_validate(
            {
                "id": api_key.id,  # type: ignore[attr-defined]
                "key": jwt_key,
                "created_at": api_key.created_at,
                "created_by": api_key.created_by.username if api_key.created_by else None,
            }
        )

    model_config = ConfigDict(from_attributes=True)
