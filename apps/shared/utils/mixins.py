import typing as t

from rest_framework.request import Request

from apps.shared.utils.exceptions import raise_validation_error
from apps.shared.utils.logging import logger


class RequestContextMixin:
    """
    Implements request property for serializers (from context).

    If serializer does not contain request in context,
    it will raise RunTimeError not while the server is running
    and whole process is running.

    Prevention of future bugs!
    """

    @property
    def request(self) -> Request:
        if (request := self.context.get("request")) is None:
            raise RuntimeError("request was not provided in serializer context.")

        return request


class RequiredFieldsMixin:
    """
    Mixin to ensure that specified fields are present and not blank/null.
    Usage: define `required_fields` in your serializer.
    """

    required_fields: list[str] = []

    def validate(self, attrs: dict[str, t.Any]) -> dict[str, t.Any]:
        # Check for missing or empty fields
        logger.info(f"RequiredFieldsMixin.validate called")
        logger.info(f"Required fields: {self.required_fields}")
        logger.info(f"Available attributes: {list(attrs.keys())}")

        for field in getattr(self, 'required_fields', []):
            value = attrs.get(field)

            logger.info(f"Validating required field '{field}': {value}")
            if value in [None, '']:
                raise_validation_error(message=f"The field '{field}' is required and cannot be blank.")

        return super().validate(attrs)
