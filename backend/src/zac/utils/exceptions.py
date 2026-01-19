import logging
import os
import re
import uuid
from collections import OrderedDict
from typing import List, Optional, Union

from django.forms.utils import ErrorList
from django.http import Http404
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from djangorestframework_camel_case.util import camelize_re, underscore_to_camel
from requests import HTTPError
from rest_framework import exceptions, exceptions as drf_exceptions, serializers, status
from rest_framework.exceptions import (
    APIException,
    PermissionDenied,
    ReturnList,
    _get_error_details,
)
from rest_framework.response import Response
from rest_framework.settings import api_settings as drf_settings
from rest_framework.views import exception_handler as drf_exception_handler
from zds_client.client import ClientError

try:
    from raven.contrib.django.raven_compat.models import client as sentry_client
except ImportError:

    class Client:
        def captureException(self):
            pass

    sentry_client = Client()

ERROR_CONTENT_TYPE = "application/problem+json"
logger = logging.getLogger(__name__)


def _underscore_to_camel(to_camelize: str) -> str:
    return re.sub(
        camelize_re,
        underscore_to_camel,
        to_camelize,
    )


def _translate_exceptions(exc):
    # Taken from DRF default exc handler
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    return exc


class FoutSerializer(serializers.Serializer):
    """
    Adapted from vng_api_common.exceptions.FoutSerializer
    Formaat van HTTP 4xx en 5xx fouten.
    """

    type = serializers.CharField(
        help_text="URI referentie naar het type fout, bedoeld voor developers",
        required=False,
        allow_blank=True,
    )
    # not according to DSO, but possible for programmatic checking
    code = serializers.CharField(help_text="Systeemcode die het type fout aangeeft")
    title = serializers.CharField(help_text="Generieke titel voor het type fout")
    status = serializers.IntegerField(help_text="De HTTP status code")
    detail = serializers.CharField(
        help_text="Extra informatie bij de fout, indien beschikbaar"
    )
    instance = serializers.CharField(
        help_text="URI met referentie naar dit specifiek voorkomen van de fout. Deze kan "
        "gebruikt worden in combinatie met server logs, bijvoorbeeld."
    )


class FieldValidationErrorSerializer(serializers.Serializer):
    """
    Formaat van validatiefouten.
    Adapted from vng_api_common.exceptions.FieldValidationErrorSerializer
    """

    name = serializers.CharField(help_text="Naam van het veld met ongeldige gegevens")
    code = serializers.CharField(help_text="Systeemcode die het type fout aangeeft")
    reason = serializers.CharField(
        help_text="Uitleg wat er precies fout is met de gegevens"
    )


class ValidatieFoutSerializer(FoutSerializer):
    """
    Adapted from vng_api_common.exceptions.ValidatieFoutSerializer
    """

    invalid_params = FieldValidationErrorSerializer(many=True)


class ExternalAPIException(APIException):
    default_detail = _("An error occurred in an external API.")

    def __init__(
        self,
        default_detail: Optional[str] = None,
        detail: Optional[str] = None,
        code: str = "error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        if default_detail:
            self.default_detail = default_detail

        super().__init__(detail=detail, code=code)
        self.status_code = status_code


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


def get_validation_errors(validation_errors: dict):
    """
    Adapted from vng_api_common.exceptions.get_validation_errors.

    """
    for field_name, error_list in validation_errors.items():
        # nested validation for fields where many=True
        if isinstance(error_list, list):
            for i, nested_error_dict in enumerate(error_list):
                if isinstance(nested_error_dict, dict):
                    for err in get_validation_errors(nested_error_dict):
                        err["name"] = (
                            f"{_underscore_to_camel(field_name)}.{i}.{err['name']}"
                        )
                        yield err
                elif isinstance(nested_error_dict, list):
                    for j, err in enumerate(nested_error_dict):
                        for _err in get_validation_errors(
                            {f"{_underscore_to_camel(field_name)}.{j}": err}
                        ):
                            yield _err

        # nested validation - recursively call the function
        if isinstance(error_list, dict):
            for err in get_validation_errors(error_list):
                err["name"] = f"{_underscore_to_camel(field_name)}.{err['name']}"
                yield err
            continue

        if isinstance(error_list, exceptions.ErrorDetail):
            error_list = [error_list]

        for error in error_list:
            if isinstance(error, dict):
                continue
            elif isinstance(error, list):
                continue

            else:
                yield OrderedDict(
                    [
                        # see https://tools.ietf.org/html/rfc7807#section-3.1
                        # ('type', 'about:blank'),
                        ("name", _underscore_to_camel(field_name)),
                        ("code", error.code),
                        ("reason", str(error)),
                    ]
                )


ErrorSerializer = Union[FoutSerializer, ValidatieFoutSerializer]


class HandledException:
    """
    Adapted from vng_api_common.exceptions.HandledException

    """

    def __init__(self, exc: exceptions.APIException, response, request=None):
        self.exc = exc
        assert 400 <= response.status_code < 600, "Unsupported status code"
        self.response = response
        self.request = request

        self._exc_id = str(uuid.uuid4())

    @property
    def _error_detail(self) -> str:
        if isinstance(self.exc, drf_exceptions.ValidationError) or isinstance(
            self.exc, drf_exceptions.PermissionDenied
        ):
            # ErrorDetail from DRF is a str subclass
            data = getattr(self.response, "data", {})
            if isinstance(data, dict):
                if detail := data.get("detail"):
                    return detail
                elif detail := data.get(drf_settings.NON_FIELD_ERRORS_KEY):
                    if isinstance(detail, list):
                        return " ".join([str(det) for det in detail])
                    elif isinstance(detail, str):
                        return detail

            return _get_error_details(data)
        # any other exception -> return the raw ErrorDetails object so we get
        # access to the code later
        return self.exc.detail

    @classmethod
    def as_serializer(
        cls, exc: exceptions.APIException, response, request=None
    ) -> ErrorSerializer:
        """
        Return the appropriate serializer class instance.
        """
        exc = _translate_exceptions(exc)
        self = cls(exc, response, request)
        self.log()

        if isinstance(exc, exceptions.ValidationError):
            serializer_class = ValidatieFoutSerializer
        else:
            serializer_class = FoutSerializer

        return serializer_class(instance=self)

    def log(self):
        logger.exception("Exception %s ocurred", self._exc_id)

    @property
    def type(self) -> str:
        exc_detail_url = ""
        if self.request is not None:
            exc_detail_url = self.request.build_absolute_uri(exc_detail_url)
        return exc_detail_url

    @property
    def code(self) -> str:
        if isinstance(self.exc, exceptions.ValidationError) or isinstance(
            self.exc, drf_exceptions.PermissionDenied
        ):
            return self.exc.default_code
        return self._error_detail.code if self._error_detail else ""

    @property
    def title(self) -> str:
        """
        Return the generic message for this type of exception.
        """
        default_title = getattr(self.exc, "default_detail", str(self._error_detail))
        return default_title

    @property
    def status(self) -> int:
        return self.response.status_code

    @property
    def detail(self) -> str:
        return str(self._error_detail)

    @property
    def instance(self) -> str:
        return f"urn:uuid:{self._exc_id}"

    @property
    def invalid_params(self) -> Union[None, List]:
        if isinstance(self.exc.detail, ReturnList) or isinstance(self.exc.detail, list):
            return [
                error for exc in self.exc.detail for error in get_validation_errors(exc)
            ]
        else:
            return [error for error in get_validation_errors(self.exc.detail)]


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

        if isinstance(exc, HTTPError):
            status_code = getattr(
                exc.response, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            exc = ExternalAPIException(
                detail=exc.args[0],
                status_code=status_code,
            )
            response = Response(status=status_code)
        elif isinstance(exc, ClientError):
            status_code = int(
                exc.args[0].get("status", status.HTTP_500_INTERNAL_SERVER_ERROR)
            )
            code = exc.args[0].get("code", "error")
            detail = exc.args[0].get("title", force_str(exc.args[0]))
            exc = ExternalAPIException(
                detail=detail,
                code=code,
                status_code=status_code,
            )
            response = Response(status=status_code)
        else:
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
