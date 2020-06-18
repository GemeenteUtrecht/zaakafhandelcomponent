import mimetypes
from typing import Any, Optional

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from ..services import download_document


def _cast(value: Optional[Any], type_: type) -> Any:
    if value is None:
        return value
    return type_(value)


class DownloadDocumentView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        versie = _cast(request.GET.get("versie", None), int)
        document, content = download_document(versie=versie, **kwargs)
        content_type = (
            document.formaat or mimetypes.guess_type(document.bestandsnaam)[0]
        )
        response = HttpResponse(content, content_type=content_type)
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{document.bestandsnaam}"'
        return response
