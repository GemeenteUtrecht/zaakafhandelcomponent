from typing import Any, Optional

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import authentication, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.api_models.documenten import Document

from zac.api.utils import remote_schema_ref
from zac.core.api.permissions import CanOpenDocuments
from zac.core.cache import invalidate_document_cache
from zac.core.services import find_document, get_document

from .api import create_doc, patch_and_destroy_doc
from .exceptions import DOWCCreateError
from .serializers import DowcResponseSerializer, DowcSerializer


def _cast(value: Optional[Any], type_: type) -> Any:
    if value is None:
        return value
    return type_(value)


@extend_schema(
    summary=_("Retrieve a document."),
    parameters=[
        OpenApiParameter(
            name="versie",
            required=False,
            type=OpenApiTypes.URI,
            description=_("Version of the document."),
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class OpenDowcView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanOpenDocuments,)
    document = None
    serializer_class = DowcResponseSerializer

    def get_object(self, bronorganisatie: str, identificatie: str) -> Document:
        versie = _cast(self.request.GET.get("versie", None), int)
        document = find_document(bronorganisatie, identificatie, versie=versie)
        return document

    def post(self, request, bronorganisatie, identificatie, purpose):
        """
        Create a dowc object in the dowc API and expose the document through a URL.
        """
        document = self.get_object(bronorganisatie, identificatie)
        referer = request.headers.get("referer", "")
        try:
            response, status_code = create_doc(request.user, document, purpose, referer)
        except DOWCCreateError as err:
            raise ValidationError(err.args[0])

        serializer = self.serializer_class(response)

        invalidate_document_cache(document)
        return Response(serializer.data, status=status_code)


class DeleteDowcView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanOpenDocuments,)
    serializer_class = DowcSerializer

    @extend_schema(
        summary=_("Update and delete a document."),
        responses={
            (200, "application/json"): remote_schema_ref(
                settings.DOWC_API_SCHEMA,
                ["components", "schemas", "UnlockedDocument"],
            ),
        },
    )
    def delete(self, request, dowc_uuid):
        """
        Delete the dowc object in the dowc API. This implies that the dowc will
        attempt to patch the document in the DRC API.
        """
        serializer = self.serializer_class(data={"uuid": dowc_uuid})
        serializer.is_valid(raise_exception=True)
        data = patch_and_destroy_doc(request.user, serializer.validated_data["uuid"])

        # Invalidate cache if valid response
        if "versionedUrl" in data:
            document = get_document(data["versionedUrl"])
            invalidate_document_cache(document)

        return Response(data)
