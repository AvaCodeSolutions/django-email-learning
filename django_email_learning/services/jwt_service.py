from django.conf import settings
from django.utils import timezone
import datetime
import jwt


ALGORITHM = "HS256"


class InvalidTokenException(Exception):
    pass


class ExpiredTokenException(Exception):
    pass


def _secret() -> str:
    return settings.DJANGO_EMAIL_LEARNING["JWT_SECRET_KEY"]


def generate_jwt(
    payload: dict,
    expiration_seconds: int = 3600,
    exp: datetime.datetime | None = None,
) -> str:
    payload_copy = payload.copy()
    if not exp:
        exp = timezone.now() + datetime.timedelta(seconds=expiration_seconds)
    payload_copy["exp"] = exp
    token = jwt.encode(payload_copy, _secret(), algorithm=ALGORITHM)  # type: ignore[arg-type]
    return token


def decode_jwt(token: str) -> dict:
    try:
        decoded = jwt.decode(token, _secret(), algorithms=[ALGORITHM])  # type: ignore[arg-type]
        return decoded
    except (jwt.InvalidSignatureError, jwt.DecodeError, jwt.InvalidAlgorithmError):
        raise InvalidTokenException("The signature is invalid")
    except jwt.ExpiredSignatureError:
        raise ExpiredTokenException("The token is not valid anymore")
