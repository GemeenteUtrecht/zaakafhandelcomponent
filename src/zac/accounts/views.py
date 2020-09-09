from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView as _LoginView
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from zac.core.services import find_zaak

from .forms import (
    AccessRequestForm,
    AuthorizationProfileForm,
    PermissionSetForm,
    UserAuthorizationProfileForm,
)
from .models import (
    AccessRequest,
    AuthorizationProfile,
    PermissionSet,
    UserAuthorizationProfile,
)


class LoginView(_LoginView):
    template_name = "accounts/login.html"


class AuthorizationProfileListView(LoginRequiredMixin, ListView):
    queryset = AuthorizationProfile.objects.prefetch_related(
        "user_set", "permission_sets"
    )


class AuthorizationProfileCreateView(PermissionRequiredMixin, CreateView):
    model = AuthorizationProfile
    form_class = AuthorizationProfileForm
    permission_required = "accounts.add_authorizationprofile"
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
    permission_required = "accounts.add_permissionset"
    success_url = reverse_lazy("accounts:authprofile-list")


class PermissionSetDetailView(LoginRequiredMixin, DetailView):
    queryset = PermissionSet.objects.prefetch_related("authorizationprofile_set")
    context_object_name = "permission_set"


class PermissionSetUpdateView(PermissionRequiredMixin, UpdateView):
    model = PermissionSet
    form_class = PermissionSetForm
    permission_required = "accounts.change_permissionset"


class UserAuthorizationProfileCreateView(PermissionRequiredMixin, CreateView):
    model = UserAuthorizationProfile
    permission_required = "accounts.add_userauthorizationprofile"
    form_class = UserAuthorizationProfileForm

    def _get_auth_profile(self):
        if not hasattr(self, "_auth_profile"):
            self._auth_profile = get_object_or_404(
                AuthorizationProfile, uuid=self.kwargs["uuid"]
            )
        return self._auth_profile

    def get_form_kwargs(self):
        default = super().get_form_kwargs()
        kwargs = {
            "auth_profile": self._get_auth_profile(),
        }
        return {**default, **kwargs}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "auth_profile": self._get_auth_profile(),
            }
        )
        return context

    def get_success_url(self):
        return reverse(
            "accounts:authprofile-detail",
            kwargs={"uuid": self.object.auth_profile.uuid},
        )


class AccessRequestCreateView(LoginRequiredMixin, FormView):
    form_class = AccessRequestForm
    template_name = "accounts/accessrequest_form.html"
    #  todo add thanks page?
    success_url = reverse_lazy("core:index")

    def get_zaak(self):
        return find_zaak(**self.request.resolver_match.kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs["requester"] = self.request.user
        kwargs["zaak"] = self.get_zaak()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"zaak": self.get_zaak()})
        return context

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
