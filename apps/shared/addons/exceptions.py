from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    _get_error_details,
    PermissionDenied,
)
from rest_framework.views import exception_handler

from django.utils.translation import gettext_lazy as _


from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
)


class CustomValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Invalid input.")
    default_code = "invalid"

    def __init__(self, detail=None, code=None):
        if detail is None:
            detail = self.default_detail
        if code is None:
            code = self.default_code

        # For validation failures, we may collect many errors together,
        # so the details should always be coerced to a list if not already.
        if isinstance(detail, tuple):
            detail = dict(detail)
        elif not isinstance(detail, dict) and not isinstance(detail, list):
            detail = {detail}

        self.detail = _get_error_details(detail, code)

        self.detail["success"] = False
        self.detail["code"] = int(self.detail["code"])
        self.detail["data"] = (
            None if self.detail["data"] == "None" else self.detail["data"]
        )


def raise_validation_error(data=None, message="Error", code=400):
    raise CustomValidationError(
        {
            "success": False,
            "code": int(code),
            "message": _(message),
            "data": data,
        }
    )


class CustomPermissionDenied(APIException):
    status_code = 403
    default_detail = "Sizda bu sahifani ko'rish uchun ruxsat yo'q"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, (PermissionDenied, CustomPermissionDenied)):
        custom_data = {"detail": "Sizda bu sahifani ko'rish uchun ruxsat yo'q"}
        response.data = custom_data

    return response


class CustomPasswordValidator:
    def validate(self, password, user=None):  # noqa
        MinimumLengthValidator().validate(password)
        NumericPasswordValidator().validate(password)
        CommonPasswordValidator().validate(password, user)
