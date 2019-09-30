from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView
from .models import RegieZaakConfiguratie


class IndexView(ListView):
    # queryset = (
    #     RegieZaakConfiguratie.objects.order_by("pk")
    # )
    model = RegieZaakConfiguratie
    template_name = "regiezaken/index.html"


class RegieZaakDetailView(DetailView):
    model = RegieZaakConfiguratie
    template_name = "regiezaken/regiezaak_detail.html"
