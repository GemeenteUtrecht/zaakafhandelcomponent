from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView as _LoginView
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from ..core.services import get_informatieobjecttypen
from .forms import (
    AuthorizationProfileForm,
    InformatieobjecttypeFormSet,
    PermissionSetForm,
    UserAuthorizationProfileForm,
    get_catalogus_choices,
)
from .mixins import InformatieobjecttypeFormsetMixin
from .models import (
    AuthorizationProfile,
    InformatieobjecttypePermission,
    PermissionSet,
    UserAuthorizationProfile,
)


class LoginView(_LoginView):
    template_name = "accounts/login.html"


class AuthorizationProfileListView(LoginRequiredMixin, ListView):
    queryset = AuthorizationProfile.objects.prefetch_related(
        "user_set", "permission_sets"
    ).select_related("oo")


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


class InformatieobjecttypenJSONView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        """Return the informatieobjecttypen for a catalogus"""
        informatieobjecttypen = get_informatieobjecttypen(
            catalogus=request.GET["catalogus"]
        )

        response_data = {"formData": [], "emptyFormData": []}
        for informatieobjecttype in informatieobjecttypen:
            response_data["emptyFormData"].append(
                {
                    "catalogus": request.GET["catalogus"],
                    "omschrijving": informatieobjecttype.omschrijving,
                    "selected": False,
                }
            )
        return JsonResponse(response_data)


class PermissionSetsView(LoginRequiredMixin, ListView):
    queryset = PermissionSet.objects.all()


class PermissionSetCreateView(
    PermissionRequiredMixin, InformatieobjecttypeFormsetMixin, CreateView
):
    model = PermissionSet
    form_class = PermissionSetForm
    permission_required = "accounts.add_permissionset"
    success_url = reverse_lazy("accounts:authprofile-list")

    def get(self, request, *args, **kwargs):
        self.object = None
        informatieobjecttype_formset = self.construct_formset()
        permissionset_form = self.get_form(self.form_class)
        return self.render_to_response(
            self.get_context_data(
                form=permissionset_form,
                informatieobjecttype_formset=informatieobjecttype_formset,
            )
        )

    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        self.object = None
        permissionset_form = self.get_form(self.form_class)
        informatieobjecttype_formset = self.construct_formset()

        if (
            not permissionset_form.is_valid()
            or not informatieobjecttype_formset.is_valid()
        ):
            return self.form_invalid(permissionset_form, informatieobjecttype_formset)

        return self.form_valid(permissionset_form, informatieobjecttype_formset)


class PermissionSetDetailView(LoginRequiredMixin, DetailView):
    queryset = PermissionSet.objects.prefetch_related("authorizationprofile_set")
    context_object_name = "permission_set"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        informatieobjecttype_permissions = (
            InformatieobjecttypePermission.objects.filter(
                permission_set=context["object"]
            )
        )

        if informatieobjecttype_permissions.exists():
            catalog_choices = get_catalogus_choices()
            chosen_catalog_url = informatieobjecttype_permissions.first().catalogus
            for catalog_url, catalog_label in catalog_choices:
                if catalog_url == chosen_catalog_url:
                    context["informatieobjecttype_catalogus"] = catalog_label
                    break
            context["informatieobjecttype_permissions"] = [
                {
                    "omschrijving": permission.omschrijving,
                    "max_va": permission.max_va.replace("_", " "),
                }
                for permission in informatieobjecttype_permissions
                if permission.omschrijving != ""
            ]
        return context


class PermissionSetUpdateView(
    PermissionRequiredMixin, InformatieobjecttypeFormsetMixin, UpdateView
):
    model = PermissionSet
    form_class = PermissionSetForm
    permission_required = "accounts.change_permissionset"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        informatieobjecttype_formset = self.construct_formset()
        permissionset_form = self.get_form(self.form_class)
        return self.render_to_response(
            self.get_context_data(
                form=permissionset_form,
                informatieobjecttype_formset=informatieobjecttype_formset,
            )
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        permissionset_form = self.get_form(self.form_class)
        informatieobjecttype_formset = self.construct_formset()

        if (
            not permissionset_form.is_valid()
            or not informatieobjecttype_formset.is_valid()
        ):
            return self.form_invalid(permissionset_form, informatieobjecttype_formset)

        return self.form_valid(permissionset_form, informatieobjecttype_formset)


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
