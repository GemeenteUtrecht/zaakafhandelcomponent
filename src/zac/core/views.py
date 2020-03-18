import mimetypes

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views import View

import requests

from .base_views import BaseDetailView, BaseListView
from .forms import ZakenFilterForm
from .services import (
    fetch_zaaktype,
    find_document,
    find_zaak,
    get_documenten,
    get_statussen,
    get_zaaktypes,
    get_zaken,
)


class Index(LoginRequiredMixin, BaseListView):
    """
    Display the landing screen.
    """

    template_name = "core/index.html"
    context_object_name = "zaken"
    filter_form_class = ZakenFilterForm

    def get_object_list(self):
        filter_form = self.get_filter_form()
        if filter_form.is_valid():
            filters = filter_form.as_filters()
        else:
            filters = {}
        return get_zaken(**filters)

    def get_filter_form_initial(self):
        return {"zaaktypen": [zt.url for zt in get_zaaktypes()]}


class ZaakDetail(LoginRequiredMixin, BaseDetailView):
    template_name = "core/zaak_detail.html"
    context_object_name = "zaak"

    def get_object(self):
        return find_zaak(**self.kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "zaaktype": fetch_zaaktype(self.object.zaaktype),
                "statussen": get_statussen(self.object),
                "documenten": get_documenten(self.object),
            }
        )
        return context


class DownloadDocumentView(LoginRequiredMixin, View):
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


class FlushCacheView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        referer = request.META["HTTP_REFERER"]
        cache.clear()
        return redirect(referer)
