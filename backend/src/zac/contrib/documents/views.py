from typing import Any, NoReturn, Optional

from django.http import HttpResponse

from rest_framework import authentication, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rules.contrib.views import PermissionRequiredMixin

from zac.core.permissions import zaken_download_documents
from zac.core.services import find_document

from .api import delete_document, get_document
from .serializers import DocRequestSerializer


def _cast(value: Optional[Any], type_: type) -> Any:
    if value is None:
        return value
    return type_(value)


class DocumentView(PermissionRequiredMixin, APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    permission_required = zaken_download_documents.name
    http_method_names = ["post", "delete"]
    document = None
    serializer_class = DocRequestSerializer

    def get_object(self, request, **kwargs) -> NoReturn:
        if not self.document:
            versie = _cast(request.GET.get("versie", None), int)
            self.document = find_document(versie=versie, **kwargs)

    def get_source_url(self, request, **kwargs) -> str:
        self.get_object(request, **kwargs)
        return self.document.url

    def post(self, request, purpose, **kwargs):
        drc_url = self.get_source_url(request, **kwargs)
        doc_request = get_document(request.user, drc_url, purpose)
        serializer = self.serializer_class(doc_request)
        return Response(serializer.data)

    def delete(self, request, doc_request_uuid):
        response = delete_document(request.user, doc_request_uuid)
        return response
