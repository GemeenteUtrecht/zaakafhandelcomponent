import mimetypes

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from ..services import download_document


class DownloadDocumentView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        document, content = download_document(**kwargs)
        content_type = (
            document.formaat or mimetypes.guess_type(document.bestandsnaam)[0]
        )
        response = HttpResponse(content, content_type=content_type)
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{document.bestandsnaam}"'
        return response
