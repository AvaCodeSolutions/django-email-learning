from django_email_learning.services import jwt_service
from freezegun import freeze_time
from datetime import timedelta, datetime
import jwt
import pytest


def test_jwt_service_generate_and_decode_jwt():
    payload = {"user_id": 123, "email": "test@example.com"}
    token = jwt_service.generate_jwt(payload)
    decoded_payload = jwt_service.decode_jwt(token)
    assert decoded_payload["user_id"] == payload["user_id"]
    assert decoded_payload["email"] == payload["email"]


def test_jwt_service_token_expiration():
    payload = {"user_id": 456}

    # Freeze time at a specific moment
    with freeze_time("2023-01-01 12:00:00") as frozen_time:
        token = jwt_service.generate_jwt(payload, expiration_seconds=3600)

        # Fast forward time by 4000 seconds
        frozen_time.tick(delta=timedelta(seconds=4000))

        # Token should now be expired
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_service.decode_jwt(token)


def test_jwt_service_invalid_token():
    payload = {"user_id": 789}
    payload_copy = payload.copy()
    payload_copy["exp"] = datetime.utcnow() + timedelta(seconds=3600)
    # Create an invalid token by altering the signature
    invalid_token = jwt.encode(
        payload_copy, "INVALID_SECRET", algorithm=jwt_service.ALGORITHM
    )

    with pytest.raises(jwt.InvalidSignatureError):
        jwt_service.decode_jwt(invalid_token)
