from typing import Any, Optional

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import authentication, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.api_models.documenten import Document

from zac.core.api.permissions import CanReadDocuments
from zac.core.services import find_document
from zac.core.utils import cast

from .api import create_doc, patch_and_destroy_doc
from .serializers import DeleteDowcSerializer, DowcResponseSerializer, DowcSerializer


class ContezzaDocumentView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadDocuments,
    )
    document = None

    def get_object(self, bronorganisatie: str, identificatie: str) -> Document:
        versie = cast(self.request.GET.get("versie", None), int)
        document = find_document(bronorganisatie, identificatie, versie=versie)
        self.check_object_permissions(self.request, document)
        return document
