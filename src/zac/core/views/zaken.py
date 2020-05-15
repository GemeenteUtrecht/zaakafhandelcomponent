from concurrent import futures
from itertools import groupby
from typing import Any, Dict, List

from django.urls import reverse
from django.views.generic import FormView, TemplateView

from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.mixins import PermissionRequiredMixin
from zac.accounts.permissions import UserPermissions
from zac.advices.models import Advice

from ..base_views import BaseDetailView, BaseListView, SingleObjectMixin
from ..forms import ZaakAfhandelForm, ZakenFilterForm
from ..permissions import zaken_close, zaken_inzien, zaken_set_result
from ..services import (
    find_zaak,
    get_documenten,
    get_related_zaken,
    get_resultaat,
    get_rollen,
    get_statussen,
    get_zaak_eigenschappen,
    get_zaakobjecten,
    get_zaaktypen,
    get_zaken,
)
from ..zaakobjecten import GROUPS, ZaakObjectGroup
from .utils import get_zaak_from_query


class Index(PermissionRequiredMixin, BaseListView):
    """
    Display the landing screen.

    The list of zaken that can be viewed is retrieved from the APIs.

    Note that permission checks are in place - only zaken of zaaktypen are retrieved
    where you have access to the zaaktype.
    """

    template_name = "core/index.html"
    context_object_name = "zaken"
    filter_form_class = ZakenFilterForm
    permission_required = zaken_inzien.name

    def get_filter_form_kwargs(self):
        kwargs = super().get_filter_form_kwargs()
        kwargs["zaaktypen"] = get_zaaktypen(UserPermissions(self.request.user))
        return kwargs

    def get_object_list(self):
        filter_form = self.get_filter_form()
        if filter_form.is_valid():
            filters = filter_form.as_filters()
        else:
            filters = {}
        user_perms = UserPermissions(self.request.user)
        zaken = get_zaken(user_perms, **filters)[:50]

        return zaken


class ZaakDetail(PermissionRequiredMixin, BaseDetailView):
    template_name = "core/zaak_detail.html"
    context_object_name = "zaak"
    permission_required = zaken_inzien.name

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["advices"] = Advice.objects.get_for(self.object)

        with futures.ThreadPoolExecutor() as executor:
            statussen = executor.submit(get_statussen, self.object)
            _documenten = executor.submit(get_documenten, self.object)
            eigenschappen = executor.submit(get_zaak_eigenschappen, self.object)
            related_zaken = executor.submit(get_related_zaken, self.object)
            rollen = executor.submit(get_rollen, self.object)

            resultaat = executor.submit(get_resultaat, self.object)

            documenten, gone = _documenten.result()

            context.update(
                {
                    "statussen": statussen.result(),
                    "documenten": documenten,
                    "documenten_gone": gone,
                    "eigenschappen": eigenschappen.result(),
                    "resultaat": resultaat.result(),
                    "related_zaken": related_zaken.result(),
                    "rollen": rollen.result(),
                }
            )

        # count the amount of advices
        Advice.objects.set_counts([zaak for (_, zaak) in context["related_zaken"]])

        return context


class FetchZaakObjecten(PermissionRequiredMixin, TemplateView):
    """
    Retrieve the ZaakObjecten for a given zaak reference.

    Intended to be called via AJAX.
    """

    template_name = "core/includes/zaakobjecten.html"
    permission_required = zaken_inzien.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        zaak = get_zaak_from_query(self.request)
        self.check_object_permissions(zaak)

        context["zaakobjecten"] = self._get_zaakobjecten(zaak)

        return context

    def _get_zaakobjecten(self, zaak: Zaak) -> List[ZaakObjectGroup]:
        # API call
        zaakobjecten = get_zaakobjecten(zaak.url)

        def group_key(zo):
            if zo.object_type == "overige":
                return zo.object_type_overige
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


class ZaakAfhandelView(PermissionRequiredMixin, SingleObjectMixin, FormView):
    form_class = ZaakAfhandelForm
    template_name = "core/zaak_afhandeling.html"
    context_object_name = "zaak"
    permission_required = "zaken:afhandelen"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().post(request, *args, **kwargs)

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    def get_context_data(self, **kwargs) -> dict:
        context = super().get_context_data(**kwargs)
        return context

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()

        user = self.request.user
        can_set_result = user.has_perm(zaken_set_result.name, self.object)
        can_close = user.has_perm(zaken_close.name, self.object)

        return {
            "zaak": self.object,
            "can_set_result": can_set_result,
            "can_close": can_close,
            **kwargs,
        }

    def form_valid(self, form: ZaakAfhandelForm):
        form.save(user=self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("core:zaak-detail", kwargs=self.kwargs)
