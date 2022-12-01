from django.forms.utils import ErrorList
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.views import exception_handler as drf_exception_handler


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


def exception_handler(exc, context):
    """
    Update the default DRF exception handler with data when user can request permissions
    """
    response = drf_exception_handler(exc, context)

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
