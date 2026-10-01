"""Project-wide DRF exception handling.

Every error response has the same shape so clients only need one parser:

    {"error": "<human-readable message>", "details": {...}}
"""
import logging
from typing import Any, Dict, Tuple

from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

DATABASE_UNAVAILABLE_MESSAGE = "The database is currently unavailable. Please try again later."
INTERNAL_ERROR_MESSAGE = "An unexpected error occurred."
INVALID_DATA_MESSAGE = "Invalid request data."


def error_response(message: str, status_code: int, details: Any = None) -> Response:
    return Response({"error": message, "details": details or {}}, status=status_code)


def exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """Convert any exception raised in a DRF view into the standard error shape.

    - PyMongoError -> 503, since the request was fine but the database is not.
    - DRF exceptions (validation, parse errors, 405, ...) keep their status code.
    - Anything else is a bug: log it and return a generic 500 without leaking
      internals to the client.
    """
    if isinstance(exc, PyMongoError):
        logger.exception("Database error while handling %s", _view_name(context))
        return error_response(DATABASE_UNAVAILABLE_MESSAGE, status.HTTP_503_SERVICE_UNAVAILABLE)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled error while handling %s", _view_name(context))
        return error_response(INTERNAL_ERROR_MESSAGE, status.HTTP_500_INTERNAL_SERVER_ERROR)

    message, details = _describe(exc, response.data)
    response.data = {"error": message, "details": details}
    return response


def _describe(exc: Exception, data: Any) -> Tuple[str, Dict[str, Any]]:
    """Return (message, details) from the data DRF already built for `exc`.

    Validation errors carry field messages; every other DRF error is {"detail": "..."}.
    """
    if isinstance(exc, ValidationError):
        details = data if isinstance(data, dict) else {"non_field_errors": data}
        return _first_message(details), details
    return str(data.get("detail", INTERNAL_ERROR_MESSAGE)), {}


def _first_message(details: Dict[str, Any]) -> str:
    """Use the first field error as the top-level message, e.g. for display in the UI."""
    for messages in details.values():
        if isinstance(messages, list) and messages:
            return str(messages[0])
    return INVALID_DATA_MESSAGE


def _view_name(context: Dict[str, Any]) -> str:
    view = context.get("view")
    return type(view).__name__ if view else "unknown view"
