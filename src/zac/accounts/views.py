from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView as _LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import PermissionSetForm
from .models import Entitlement, PermissionSet


class LoginView(_LoginView):
    template_name = "accounts/login.html"


class EntitlementsView(LoginRequiredMixin, ListView):
    queryset = Entitlement.objects.prefetch_related("user_set", "permission_sets")


class PermissionSetsView(LoginRequiredMixin, ListView):
    queryset = PermissionSet.objects.all()


class PermissionSetCreateView(PermissionRequiredMixin, CreateView):
    model = PermissionSet
    form_class = PermissionSetForm
    permission_required = "accounts.can_add_permissionset"
    success_url = reverse_lazy("accounts:entitlements-list")
