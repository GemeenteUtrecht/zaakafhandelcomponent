from typing import Any, Dict

from django.urls import reverse
from django.views.generic import FormView

from zac.accounts.mixins import PermissionRequiredMixin

from ..base_views import BaseDetailView, SingleObjectMixin
from ..forms import BesluitForm
from ..permissions import zaken_inzien
from ..services import find_zaak, get_besluiten


class ZaakBesluitenView(PermissionRequiredMixin, BaseDetailView):
    template_name = "core/zaak_besluiten.html"
    context_object_name = "zaak"
    permission_required = zaken_inzien.name

    def get_object(self):
        zaak = find_zaak(**self.kwargs)
        self.check_object_permissions(zaak)
        return zaak

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "besluiten": get_besluiten(self.object),
            }
        )
        return context


class BesluitCreateView(PermissionRequiredMixin, SingleObjectMixin, FormView):
    template_name = "core/create_zaak_besluit.html"
    context_object_name = "zaak"
    permission_required = zaken_inzien.name
    form_class = BesluitForm

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

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        return context

    def get_form_kwargs(self):
        base = super().get_form_kwargs()
        return {
            **base,
            "zaak": self.object,
        }

    def get_success_url(self):
        return reverse("core:zaak-besluiten", kwargs=self.kwargs)
