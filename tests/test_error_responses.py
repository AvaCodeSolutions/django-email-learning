"""Exception detail must not reach clients.

`str(exception)` on a database error carries constraint and column names, and on
a connection error it can carry hostnames and credentials. These cover the
helper directly plus one endpoint end to end.
"""

import logging
from unittest.mock import patch

from django.db.utils import IntegrityError
from django.urls import reverse

from django_email_learning.error_responses import (
    CONFLICT_MESSAGE,
    UNEXPECTED_ERROR_MESSAGE,
    log_and_conflict_response,
    log_and_error_response,
)

# A realistic IntegrityError message - this is the shape of what used to be
# returned verbatim to the caller.
LEAKY_DB_ERROR = (
    'duplicate key value violates unique constraint "django_email_learning_organization_slug_key"\n'
    "DETAIL:  Key (slug)=(acme) already exists."
)

API_KEYS_URL = reverse("django_email_learning:api_platform:api_keys_list")


def test_conflict_response_returns_fixed_message_and_status():
    logger = logging.getLogger("test")

    response = log_and_conflict_response(logger, IntegrityError(LEAKY_DB_ERROR), "Saving organization data")

    assert response.status_code == 409
    body = response.content.decode()
    assert CONFLICT_MESSAGE in body
    assert "unique constraint" not in body
    assert "django_email_learning_organization_slug_key" not in body
    assert "acme" not in body


def test_error_response_returns_fixed_message_and_status():
    logger = logging.getLogger("test")

    response = log_and_error_response(logger, Exception("imap.example.com password=hunter2"), "x", status=500)

    assert response.status_code == 500
    body = response.content.decode()
    assert UNEXPECTED_ERROR_MESSAGE in body
    assert "hunter2" not in body
    assert "imap.example.com" not in body


def test_detail_is_logged_server_side(caplog):
    logger = logging.getLogger("django_email_learning.test_error_responses")

    with caplog.at_level(logging.ERROR):
        log_and_conflict_response(logger, IntegrityError(LEAKY_DB_ERROR), "Saving organization data")

    # The operator still gets the context and a traceback, just not the client.
    assert "Saving organization data failed" in caplog.text
    assert "IntegrityError" in caplog.text


def test_integrity_error_detail_does_not_reach_the_client(superadmin_client):
    with patch(
        "django_email_learning.models.ApiKey.save",
        side_effect=IntegrityError(LEAKY_DB_ERROR),
    ):
        response = superadmin_client.post(API_KEYS_URL)

    assert response.status_code == 409
    body = response.content.decode()
    assert response.json()["error"] == CONFLICT_MESSAGE
    assert "unique constraint" not in body
    assert "django_email_learning_organization_slug_key" not in body


def test_serializer_value_errors_keep_their_message(org_admin_client):
    """The fix must not swallow messages this codebase writes for the caller."""
    url = reverse(
        "django_email_learning:api_platform:organizations_detail",
        kwargs={"organization_id": 1},
    )

    response = org_admin_client.post(
        url,
        data={"name": "Acme", "description": "d", "brand_color": "not-a-color"},
        content_type="application/json",
    )

    assert response.status_code in (400, 409)
    assert "Invalid hex color" in response.content.decode()
