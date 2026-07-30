"""Helpers for failing without handing the client the exception text.

`str(exception)` on a database or third-party error carries internals worth
keeping private - constraint and column names from `IntegrityError`, hostnames
and credentials from connection errors, file paths from anything raised deeper
in the stack. These helpers log the full detail (with traceback) server-side and
return a fixed message instead.

Deliberately *not* used for exceptions whose message is written by this codebase
for the caller to read - `ValueError`s raised by the serializers, and the
domain errors like `BlockedEmailError`. Those messages are the API contract, and
several are asserted on in tests.
"""

import logging

from django.http import JsonResponse

CONFLICT_MESSAGE = "The request conflicts with existing data."
UNEXPECTED_ERROR_MESSAGE = "The request could not be completed."


def log_and_error_response(
    logger: logging.Logger,
    exception: BaseException,
    context: str,
    *,
    status: int,
    message: str = UNEXPECTED_ERROR_MESSAGE,
) -> JsonResponse:
    """Log `exception` against `context`, return `message` with `status`.

    `context` should say what was being attempted ("creating course content"),
    since the response no longer carries that information.
    """
    logger.exception("%s failed: %s", context, exception.__class__.__name__)
    return JsonResponse({"error": message}, status=status)


def log_and_conflict_response(
    logger: logging.Logger,
    exception: BaseException,
    context: str,
    *,
    status: int = 409,
) -> JsonResponse:
    """`log_and_error_response` for the integrity-error conflict case."""
    return log_and_error_response(logger, exception, context, status=status, message=CONFLICT_MESSAGE)
