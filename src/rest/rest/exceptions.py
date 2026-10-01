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
    """Turn every error raised in a view into {"error": message, "details": {...}}.

    Mongo errors become 503 (the request was fine, the database isn't), DRF errors
    keep their status code, and anything else is logged and returned as a plain 500.
    """
    view_name = type(context["view"]).__name__
    if isinstance(exc, PyMongoError):
        logger.exception("Database error in %s", view_name)
        return error_response(DATABASE_UNAVAILABLE_MESSAGE, status.HTTP_503_SERVICE_UNAVAILABLE)

    response = drf_exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled error in %s", view_name)
        return error_response(INTERNAL_ERROR_MESSAGE, status.HTTP_500_INTERNAL_SERVER_ERROR)

    message, details = _describe(exc, response.data)
    response.data = {"error": message, "details": details}
    return response


def _describe(exc: Exception, data: Any) -> Tuple[str, Dict[str, Any]]:
    # Read response.data rather than exc.detail: DRF also converts Django's Http404
    # and PermissionDenied, which have no .detail.
    if isinstance(exc, ValidationError):
        details = data if isinstance(data, dict) else {"non_field_errors": data}
        return _first_message(details), details
    return str(data.get("detail", INTERNAL_ERROR_MESSAGE)), {}


def _first_message(details: Dict[str, Any]) -> str:
    for messages in details.values():
        if isinstance(messages, list) and messages:
            return str(messages[0])
    return INVALID_DATA_MESSAGE
