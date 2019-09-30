from django.views.generic import ListView, DetailView
from .models import RegieZaakConfiguratie
from zac.core.services import get_zaken


class IndexView(ListView):
    model = RegieZaakConfiguratie
    template_name = "regiezaken/index.html"


class RegieZaakDetailView(DetailView):
    model = RegieZaakConfiguratie
    template_name = "regiezaken/regiezaak_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['zaken'] = get_zaken([])

        return context
