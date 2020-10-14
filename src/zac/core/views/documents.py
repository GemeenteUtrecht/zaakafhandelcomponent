import mimetypes
from typing import Any, Optional

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from ..services import download_document, find_document, get_informatieobjecttype
from .mixins import DocumentPermissionMixin


def _cast(value: Optional[Any], type_: type) -> Any:
    if value is None:
        return value
    return type_(value)


class DownloadDocumentView(LoginRequiredMixin, DocumentPermissionMixin, View):
    def get(self, request, *args, **kwargs):
        versie = _cast(request.GET.get("versie", None), int)
        document = find_document(versie=versie, **kwargs)

        informatieobjecttype = get_informatieobjecttype(document.informatieobjecttype)
        document.informatieobjecttype = informatieobjecttype
        self.check_document_permissions(document, self.request.user)

        content_type = (
            document.formaat or mimetypes.guess_type(document.bestandsnaam)[0]
        )

        document, content = download_document(document)
        response = HttpResponse(content, content_type=content_type)
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{document.bestandsnaam}"'
        return response
