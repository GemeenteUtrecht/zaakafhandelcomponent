from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect

from .forms import InformatieobjecttypeFormSet


class PermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    def check_object_permissions(self, obj):
        user = self.request.user
        perms_required = self.get_permission_required()
        if not user.has_perms(perms_required, obj=obj):
            raise PermissionDenied(self.get_permission_denied_message())


class InformatieobjecttypeFormsetMixin:
    def construct_formset(self):
        formset_kwargs = self.get_formset_kwargs()
        return InformatieobjecttypeFormSet(**formset_kwargs)

    # taken from extra_views.formsets.BaseFormSetFactory
    def get_formset_kwargs(self):
        """
        Returns the keyword arguments for instantiating the formset.
        """
        kwargs = {"initial": self.get_initial()}

        if self.object:
            kwargs["instance"] = self.object

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {"data": self.request.POST.copy(), "files": self.request.FILES}
            )
        return kwargs

    def get_initial(self):
        return []

    def form_valid(self, permissionset_form, informatieobjecttype_formset):
        self.object = permissionset_form.save()
        informatieobjecttype_formset.instance = self.object
        # takes care of creating, updating and deleting
        informatieobjecttype_formset.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, permissionset_form, informatieobjecttype_formset):
        return self.render_to_response(
            self.get_context_data(
                form=permissionset_form,
                informatieobjecttype_formset=informatieobjecttype_formset,
            )
        )
