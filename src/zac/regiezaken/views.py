from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from zac.core.base_views import BaseDetailView
from zac.core.services import (
    get_eigenschappen,
    get_related_zaken,
    get_statussen,
    get_zaak,
    get_zaaktypes,
    get_zaken,
)

from .camunda import get_tasks
from .models import RegieZaakConfiguratie


class IndexView(LoginRequiredMixin, ListView):
    model = RegieZaakConfiguratie
    template_name = "regiezaken/index.html"


class RegieZaakDetailView(LoginRequiredMixin, DetailView):
    model = RegieZaakConfiguratie
    template_name = "regiezaken/regiezaak_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        instance = self.get_object()
        context["zaken"] = get_zaken(zaaktypes=[instance.zaaktype_main])

        return context


class ZaakDetailView(BaseDetailView):
    template_name = "regiezaken/zaak_detail.html"
    context_object_name = "zaak"

    def get_object(self):
        uuid = self.kwargs["uuid"]
        zaak = get_zaak(zaak_uuid=uuid)
        zaak.tasks = get_tasks(zaak)
        zaak.eigenschappen = get_eigenschappen(zaak)
        zaak.statussen = get_statussen(zaak)
        return zaak

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        id = int(self.kwargs["pk"])
        regie = RegieZaakConfiguratie.objects.get(id=id)
        _related_zaken = get_related_zaken(self.get_object(), regie.zaaktypes_related)

        all_zaaktypes = {zaaktype.url: zaaktype for zaaktype in get_zaaktypes()}

        # add tasks to zaken:
        related_zaken = []

        for zaak in _related_zaken:
            _zaaktype = all_zaaktypes[zaak.zaaktype]
            zaak.tasks = get_tasks(zaak)
            zaak.eigenschappen = get_eigenschappen(zaak)
            zaak.statussen = get_statussen(zaak)
            related_zaken.append((_zaaktype, zaak))

        context["regie"] = regie
        context["zaaktype"] = regie.zaaktype_object
        context["related_zaken"] = related_zaken

        return context
