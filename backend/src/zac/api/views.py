from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

import requests
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.core.models import WarningBanner

HEADERS_TO_KEEP = (
    "api-version",
    "content-type",
    "x-oas-version",
)

from django.conf import settings

from zac.core.utils import A_DAY
from zac.utils.decorators import cache


@cache("remote_schema:{schema_url}", timeout=A_DAY)
def get_schema_url(schema_url: str):
    return requests.get(schema_url)


def remote_schema_view(request):
    schema_url = request.GET["schema"]
    if schema_url not in settings.EXTERNAL_API_SCHEMAS.values():
        raise PermissionDenied

    response = get_schema_url(schema_url)
    content = response.content

    django_response = HttpResponse(content=content)
    for header, value in response.headers.items():
        if header.lower() not in HEADERS_TO_KEEP:
            continue
        django_response[header] = value
    return django_response


class HealthCheckView(APIView):
    permission_classes = []
    authentication_classes = []

    @extend_schema(
        summary=_("Retrieve health check."),
        description=_("Returns the health check status."),
        responses={
            "200": inline_serializer(
                "HealthCheckSerializer",
                fields={"healthy": serializers.BooleanField(default=True)},
            )
        },
    )
    def get(self, request: Request, *args, **kwargs):
        return Response({"healty": True})

    def get_serializer(self, *args, **kwargs):
        # shut up drf-spectacular
        return dict()


class PingView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        "ping",
        summary=_("Ping a user session."),
        description=_("Extends user session on activity."),
        request=None,
        responses={
            "200": inline_serializer(
                "PingSerializer",
                fields={
                    "pong": serializers.BooleanField(default=True),
                    "warning": serializers.CharField(
                        default=None, allow_null=True, allow_blank=True
                    ),
                },
            )
        },
    )
    def get(self, request: Request, *args, **kwargs):
        response = {"pong": True}
        warning = WarningBanner.get_solo()
        if warning.warning:
            response["warning"] = warning.warning

        return Response(response)

    def get_serializer(self, *args, **kwargs):
        # shut up drf-spectacular
        return dict()
