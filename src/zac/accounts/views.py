from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as _LoginView
from django.views.generic import ListView

from .models import Entitlement, PermissionSet


class LoginView(_LoginView):
    template_name = "accounts/login.html"


class EntitlementsView(LoginRequiredMixin, ListView):
    queryset = Entitlement.objects.prefetch_related("user_set", "permission_sets")


class PermissionSetsView(LoginRequiredMixin, ListView):
    queryset = PermissionSet.objects.all()
