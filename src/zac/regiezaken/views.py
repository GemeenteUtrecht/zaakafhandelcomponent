from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as _LoginView
from django.views.generic import DetailView, ListView

from zac.core.services import get_zaken
from zac.core.views import ZaakDetail

from .models import RegieZaakConfiguratie
from .camunda import get_process_instances


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
        context['zaken'] = get_zaken(zaaktypes=[instance.zaaktype_object.id])

        return context


class ZaakDetailView(ZaakDetail):
    template_name = 'regiezaken/zaak_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # FIXME filter by ZAAK
        context['process_instances'] = get_process_instances()

        return context
