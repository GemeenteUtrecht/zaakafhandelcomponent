from typing import Any, Optional

from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.api_models.documenten import Document

from zac.api.utils import remote_schema_ref
from zac.core.cache import invalidate_document_cache
from zac.core.services import find_document, get_document

from .api import create_doc, patch_and_destroy_doc
from .permissions import CanOpenDocuments
from .serializers import DowcResponseSerializer, DowcSerializer

DOWC_BASE = "https://dowc.utrechtproeftuin.nl/api/v1"


def _cast(value: Optional[Any], type_: type) -> Any:
    if value is None:
        return value
    return type_(value)


@extend_schema(
    summary=_("Open document for viewing or editing"),
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
        if not self.document:
            versie = _cast(self.request.GET.get("versie", None), int)
            self.document = find_document(bronorganisatie, identificatie, versie=versie)
        return self.document

    def post(self, request, bronorganisatie, identificatie, purpose):
        """
        Create a dowc object in the dowc API and expose the document through a URL.
        """
        document = self.get_object(bronorganisatie, identificatie)
        referer = request.headers.get("referer", "")
        response, status_code = create_doc(request.user, document, purpose, referer)
        if status_code == 400:
            return Response(response, status=status_code)

        serializer = self.serializer_class(response)

        # Invalidate cache
        invalidate_document_cache(document)
        return Response(serializer.data, status=status_code)


@extend_schema(
    summary=_("Finalize opened document"),
    responses={
        (200, "application/json"): remote_schema_ref(
            DOWC_BASE,
            ["components", "schemas", "UnlockedDocument"],
        ),
    },
)
class DeleteDowcView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanOpenDocuments,)
    serializer_class = DowcSerializer

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
