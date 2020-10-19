from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect


class PermissionRequiredMixin(LoginRequiredMixin, PermissionRequiredMixin):
    def check_object_permissions(self, obj):
        user = self.request.user
        perms_required = self.get_permission_required()
        if not user.has_perms(perms_required, obj=obj):
            raise PermissionDenied(self.get_permission_denied_message())


class InformatieobjecttypeFormsetMixin:
    def form_valid(self, permissionset_form, informatieobjecttype_formset):
        self.object = permissionset_form.save()
        informatieobjecttype_formset.instance = self.object
        new_informatieobjecttypen = informatieobjecttype_formset.save(commit=False)
        for form_index, informatieobjecttype in enumerate(new_informatieobjecttypen):
            form_clean_data = informatieobjecttype_formset.cleaned_data[form_index]
            if form_clean_data.get("selected"):
                if form_clean_data.get("id") is not None:
                    iot_permission = form_clean_data.get("id")
                    iot_permission.max_va = form_clean_data.get("max_va")
                else:
                    iot_permission = informatieobjecttype
                iot_permission.save()
            elif form_clean_data.get("id") is not None:
                iot_permission = form_clean_data.get("id")
                iot_permission.delete()

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, permissionset_form, informatieobjecttype_formset):
        return self.render_to_response(
            self.get_context_data(
                form=permissionset_form,
                informatieobjecttype_formset=informatieobjecttype_formset,
            )
        )
