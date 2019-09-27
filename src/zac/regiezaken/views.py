from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView
from .models import RegieZaakConfiguratie


class IndexView(LoginRequiredMixin, ListView):
    queryset = (
        RegieZaakConfiguratie.objects.order_by("-pk")
    )
    template_name = "regiezaken/index.html"
