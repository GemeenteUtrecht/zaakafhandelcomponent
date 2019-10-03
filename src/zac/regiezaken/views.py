from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as _LoginView
from django.views.generic import DetailView, ListView

from zac.core.base_views import BaseDetailView
from zac.core.services import get_related_zaken, get_zaak, get_zaken
from zac.core.views import ZaakDetail

from .camunda import get_tasks
from .models import RegieZaakConfiguratie


class LoginView(_LoginView):
    template_name = "regiezaken/login.html"


class IndexView(LoginRequiredMixin, ListView):
    model = RegieZaakConfiguratie
    template_name = "regiezaken/index.html"


class RegieZaakDetailView(LoginRequiredMixin, DetailView):
    model = RegieZaakConfiguratie
    template_name = "regiezaken/regiezaak_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        instance = self.get_object()
        context['zaken'] = get_zaken(zaaktypes=[instance.zaaktype_main])

        return context


class ZaakDetailView(BaseDetailView):
    template_name = 'regiezaken/zaak_detail.html'
    context_object_name = 'zaak'

    def get_object(self):
        uuid = self.kwargs['uuid']
        zaak = get_zaak(zaak_uuid=uuid)
        zaak.tasks = get_tasks(zaak)
        return zaak

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        id = int(self.kwargs['pk'])
        regie = RegieZaakConfiguratie.objects.get(id=id)
        related_zaken = get_related_zaken(self.get_object(), regie.zaaktypes_related)

        # add tasks to zaken:
        for zaak in related_zaken:
            zaak.tasks = get_tasks(zaak)

        context['related_zaken'] = related_zaken
        context['zaaktype'] = regie.zaaktype_object

        return context
