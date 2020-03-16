import mimetypes

from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views import View

import requests

from .base_views import BaseDetailView, BaseListView
from .forms import ZakenFilterForm
from .services import (
    find_document,
    find_zaak,
    get_documenten,
    get_statussen,
    get_zaaktypes,
    get_zaken,
)


class Index(BaseListView):
    """
    Display the landing screen.
    """

    template_name = "core/index.html"
    context_object_name = "zaken"
    filter_form_class = ZakenFilterForm

    def get_object_list(self):
        filter_form = self.get_filter_form()
        filters = {}
        if filter_form.is_valid():
            filters["zaaktypes"] = filter_form.cleaned_data["zaaktypen"]
        return get_zaken(**filters)

    def get_filter_form_initial(self):
        return {"zaaktypen": [zt.url for zt in get_zaaktypes()]}


class ZaakDetail(BaseDetailView):
    template_name = "core/zaak_detail.html"
    context_object_name = "zaak"

    def get_object(self):
        return find_zaak(**self.kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statussen"] = get_statussen(self.object)
        context["documenten"] = get_documenten(self.object)
        return context


class DownloadDocumentView(View):
    def get(self, request, *args, **kwargs):
        document = find_document(**kwargs)
        resp = requests.get(document.inhoud)

        content_type = (
            document.formaat or mimetypes.guess_type(document.bestandsnaam)[0]
        )
        response = HttpResponse(resp.content, content_type=content_type)
        response[
            "Content-Disposition"
        ] = f'attachment; filename="{document.bestandsnaam}"'
        return response


class FlushCacheView(View):
    def post(self, request, *args, **kwargs):
        referer = request.META["HTTP_REFERER"]
        cache.clear()
        return redirect(referer)
