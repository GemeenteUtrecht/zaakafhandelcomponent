from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView as _LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .forms import AuthorizationProfileForm, PermissionSetForm
from .models import AuthorizationProfile, PermissionSet


class LoginView(_LoginView):
    template_name = "accounts/login.html"


class AuthorizationProfileListView(LoginRequiredMixin, ListView):
    queryset = AuthorizationProfile.objects.prefetch_related(
        "user_set", "permission_sets"
    )


class AuthorizationProfileCreateView(PermissionRequiredMixin, CreateView):
    model = AuthorizationProfile
    form_class = AuthorizationProfileForm
    permission_required = "accounts.can_add_authorizationprofile"
    success_url = reverse_lazy("accounts:authprofile-list")


class AuthorizationProfileDetailView(LoginRequiredMixin, DetailView):
    queryset = AuthorizationProfile.objects.prefetch_related(
        "user_set", "permission_sets"
    )
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    context_object_name = "auth_profile"


class PermissionSetsView(LoginRequiredMixin, ListView):
    queryset = PermissionSet.objects.all()


class PermissionSetCreateView(PermissionRequiredMixin, CreateView):
    model = PermissionSet
    form_class = PermissionSetForm
    permission_required = "accounts.can_add_permissionset"
    success_url = reverse_lazy("accounts:authprofile-list")


class PermissionSetDetailView(LoginRequiredMixin, DetailView):
    model = PermissionSet
    context_object_name = "permission_set"
