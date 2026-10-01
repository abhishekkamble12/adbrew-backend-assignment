"""Request payload validation for the TODO API."""
from rest_framework.exceptions import ValidationError

MAX_DESCRIPTION_LENGTH = 500


def validate_todo_payload(data):
    """Validate an incoming TODO payload and return the cleaned description.

    Raises DRF's ValidationError, which the framework turns into a 400
    response with a field-level error message.
    """
    if not isinstance(data, dict):
        raise ValidationError({"non_field_errors": ["Expected a JSON object."]})

    description = data.get("description")
    if not isinstance(description, str):
        raise ValidationError({"description": ["This field is required and must be a string."]})

    description = description.strip()
    if not description:
        raise ValidationError({"description": ["This field may not be blank."]})
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValidationError(
            {"description": [f"Must be at most {MAX_DESCRIPTION_LENGTH} characters."]}
        )

    return description
