import logging
import os
from typing import List, Union

from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
    ReturnList,
    _get_error_details,
)
from rest_framework.response import Response
from vng_api_common.compat import sentry_client
from vng_api_common.exception_handling import (
    HandledException as VNGHandledException,
    get_validation_errors,
)
from vng_api_common.views import (
    ERROR_CONTENT_TYPE,
    OrderedDict,
    drf_exception_handler,
    drf_exceptions,
    status,
)

logger = logging.getLogger(__name__)


class ServiceConfigError(APIException):
    default_detail = _("A service is not configured")


def get_error_list(errors):
    """
    Given a DRF Serializer.errors, return a Django ErrorList

    """
    return ErrorList(
        [
            f"{key}: {value}"
            for key, value_list in errors.items()
            for value in value_list
        ]
    )


class HandledException(VNGHandledException):
    """
    Overwrite _error_detail "property".
    """

    @property
    def _error_detail(self) -> str:
        if isinstance(self.exc, drf_exceptions.ValidationError):
            # ErrorDetail from DRF is a str subclass
            data = getattr(self.response, "data", {})
            return _get_error_details(data)
        # any other exception -> return the raw ErrorDetails object so we get
        # access to the code later
        return self.exc.detail

    @property
    def invalid_params(self) -> Union[None, List]:
        if isinstance(self.exc.detail, ReturnList) or isinstance(self.exc.detail, list):
            return [
                error for exc in self.exc.detail for error in get_validation_errors(exc)
            ]
        else:
            return super().invalid_params


def vng_exception_handler(exc, context):
    """
    Taken from vng_api_common module and adapted.

    Transform 4xx and 5xx errors into DSO-compliant shape.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        if os.getenv("DEBUG", "").lower() in ["yes", "1", "true"]:
            return None

        logger.exception(exc.args[0], exc_info=1)
        # make sure the exception still ends up in Sentry
        sentry_client.captureException()

        # unkown type, so we use the generic Internal Server Error
        exc = drf_exceptions.APIException("Internal Server Error")
        response = Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    request = context.get("request")
    serializer = HandledException.as_serializer(
        exc, response, request
    )  # <- changed line
    response.data = OrderedDict(serializer.data.items())
    # custom content type
    response["Content-Type"] = ERROR_CONTENT_TYPE
    return response


def exception_handler(exc, context):
    """
    Update the default DRF exception handler with data when user can request permissions

    """
    response = vng_exception_handler(exc, context)

    from zac.core.api.views import ZaakDetailView

    view = context.get("view")

    if isinstance(view, ZaakDetailView) and isinstance(exc, PermissionDenied):
        return handle_zaak_permission_denied(response, context)

    return response


def handle_zaak_permission_denied(response, context):
    from zac.core.services import find_zaak

    request = context.get("request")

    zaak = find_zaak(**context.get("kwargs", {}))
    has_pending_access_request = request.user.has_pending_access_request(zaak)

    can_request_access = not has_pending_access_request
    reason = (
        _("User has pending access request for this ZAAK")
        if has_pending_access_request
        else _("User does not have required permissions.")
    )

    permission_data = {"can_request_access": can_request_access, "reason": reason}

    serializer = PermissionDeniedSerializer(instance=permission_data)
    response.data = serializer.data
    return response


class PermissionDeniedSerializer(serializers.Serializer):
    can_request_access = serializers.BooleanField(
        help_text=_("Boolean indicating if the user can request access for the ZAAK")
    )
    reason = serializers.CharField(
        max_length=1000,
        allow_blank=True,
        help_text=_("Reason why the user can't request access for the ZAAK"),
    )
