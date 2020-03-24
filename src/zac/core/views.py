import mimetypes
from itertools import groupby
from typing import List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

import requests
from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client

from .base_views import BaseDetailView, BaseListView
from .forms import ZakenFilterForm
from .services import (
    find_document,
    find_zaak,
    get_documenten,
    get_statussen,
    get_zaakobjecten,
    get_zaken,
)
from .zaakobjecten import GROUPS, ZaakObjectGroup


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
        return get_zaken(**filters)[:50]


class ZaakDetail(LoginRequiredMixin, BaseDetailView):
    template_name = "core/zaak_detail.html"
    context_object_name = "zaak"

    def get_object(self):
        return find_zaak(**self.kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
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


class FetchZaakObjecten(LoginRequiredMixin, TemplateView):
    """
    Retrieve the ZaakObjecten for a given zaak reference.

    Intended to be called via AJAX.
    """

    template_name = "core/includes/zaakobjecten.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zaak_url = self.request.GET.get("zaak")
        if not zaak_url:
            raise ValueError("Expected zaak querystring parameter")

        context["zaakobjecten"] = self._get_zaakobjecten(zaak_url)

        return context

    def _get_zaakobjecten(self, zaak_url: str) -> List[ZaakObjectGroup]:
        # API call
        zaakobjecten = get_zaakobjecten(zaak_url)

        def group_key(zo):
            return zo.object_type

        # re-group by type
        render_groups = []
        zaakobjecten = sorted(zaakobjecten, key=group_key)
        grouped = groupby(zaakobjecten, key=group_key)
        for _group, items in grouped:
            group = GROUPS.get(_group, ZaakObjectGroup(label=_group))
            group.retrieve_items(items)
            render_groups.append(group)
        return render_groups


class FetchTasks(LoginRequiredMixin, TemplateView):
    template_name = "core/includes/tasks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zaak_url = self.request.GET.get("zaak")
        if not zaak_url:
            raise ValueError("Expected zaak querystring parameter")

        context["tasks"] = self._fetch_tasks(zaak_url)
        return context

    def _fetch_tasks(self, zaak_url: str):
        client = get_client()
        tasks = client.get("task", {"processVariables": f"zaakUrl_eq_{zaak_url}"},)
        return factory(Task, tasks)


class FlushCacheView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        referer = request.META["HTTP_REFERER"]
        cache.clear()
        return redirect(referer)
