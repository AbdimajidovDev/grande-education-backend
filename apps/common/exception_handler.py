import uuid

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404

from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Barcha API xatoliklarini yagona formatga keltiradi.
    """

    response = exception_handler(exc, context)

    request = context.get("request")
    request_id = (
        request.headers.get("X-Request-ID")
        if request else None
    )

    if not request_id:
        request_id = str(uuid.uuid4())

    if response is None:
        return None

    if isinstance(exc, ValidationError):
        error_code = "validation_error"
        message = "Yuborilgan ma'lumotlarda xatolik mavjud."
        response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        details = response.data

    elif isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        error_code = "authentication_failed"
        message = "Autentifikatsiyadan o'tish talab qilinadi."
        response.status_code = status.HTTP_401_UNAUTHORIZED
        details = {}

    elif isinstance(exc, (PermissionDenied, DjangoPermissionDenied)):
        error_code = "permission_denied"
        message = "Ushbu amalni bajarish uchun ruxsatingiz yo'q."
        response.status_code = status.HTTP_403_FORBIDDEN
        details = {}

    elif isinstance(exc, Http404):
        error_code = "not_found"
        message = "So'ralgan resurs topilmadi."
        response.status_code = status.HTTP_404_NOT_FOUND
        details = {}


    elif isinstance(exc, APIException):
        error_code = str(exc.get_codes())
        message = str(exc.detail)
        details = {}

    else:
        error_code = "server_error"
        message = "Serverda kutilmagan xatolik yuz berdi."
        details = {}

    response.data = {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
        },
        "requestId": request_id,
    }

    return response
