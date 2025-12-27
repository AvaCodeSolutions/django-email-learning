from django.conf import settings
from datetime import datetime, timedelta
import jwt

SECRET = settings.SECRET_KEY
ALGORITHM = "HS256"


def generate_jwt(payload: dict, expiration_seconds: int = 3600) -> str:
    payload_copy = payload.copy()
    payload_copy["exp"] = datetime.utcnow() + timedelta(seconds=expiration_seconds)
    token = jwt.encode(payload_copy, SECRET, algorithm=ALGORITHM)
    return token


def decode_jwt(token: str) -> dict:
    decoded = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    return decoded
