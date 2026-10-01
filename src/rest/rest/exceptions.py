"""Project-wide DRF exception handling."""
import logging

from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def exception_handler(exc, context):
    """Extend DRF's handler so database failures return a clean 503.

    Without this, a PyMongoError would bubble up as an unhandled 500 (and
    leak a stack trace when DEBUG is on). Handling it centrally keeps views
    free of repetitive try/except blocks.
    """
    if isinstance(exc, PyMongoError):
        view = context.get("view")
        logger.exception("Database error in %s", type(view).__name__ if view else "unknown view")
        return Response(
            {"error": "The database is currently unavailable. Please try again later."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return drf_exception_handler(exc, context)
