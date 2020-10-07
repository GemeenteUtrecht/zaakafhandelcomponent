from typing import Dict

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
    @staticmethod
    def extract_formset_data(data) -> Dict:
        if "informatieobjecttype_catalogus" not in data:
            return {}

        modified_informatieobjecttypen = []
        for label in data:
            # Extract the omschrijving of the modified informatieobjecttypes
            if "modify" in label:
                modified_informatieobjecttypen.append(label.rstrip("-modify"))

        prefix = "informatieobjecttypepermission_set"

        formset_data = {}
        for index, omschrijving in enumerate(modified_informatieobjecttypen):
            formset_data[f"{prefix}-{index}-catalogus"] = data[
                "informatieobjecttype_catalogus"
            ]
            formset_data[f"{prefix}-{index}-max_va"] = data[f"{omschrijving}-max_va"]
            formset_data[f"{prefix}-{index}-omschrijving"] = omschrijving

            if f"{omschrijving}-id" in data:
                formset_data[f"{prefix}-{index}-id"] = data[f"{omschrijving}-id"]

        formset_data[f"{prefix}-TOTAL_FORMS"] = len(modified_informatieobjecttypen)
        formset_data[f"{prefix}-INITIAL_FORMS"] = data[f"{prefix}-INITIAL_FORMS"]
        formset_data[f"{prefix}-MIN_NUM_FORMS"] = data[f"{prefix}-MIN_NUM_FORMS"]
        formset_data[f"{prefix}-MAX_NUM_FORMS"] = data[f"{prefix}-MAX_NUM_FORMS"]

        # Case where the catalog is chosen, but no informatieobjecttypes
        if len(formset_data) == 4:
            formset_data[f"{prefix}-0-catalogus"] = data[
                "informatieobjecttype_catalogus"
            ]
            formset_data[f"{prefix}-0-max_va"] = "openbaar"  # TODO make adjustable?
            formset_data[f"{prefix}-TOTAL_FORMS"] += 1

        return formset_data

    def form_valid(self, permissionset_form, informatieobjecttype_formset):
        self.object = permissionset_form.save()
        informatieobjecttype_formset.instance = self.object
        informatieobjecttype_formset.save()

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, permissionset_form, informatieobjecttype_formset):
        return self.render_to_response(
            self.get_context_data(
                form=permissionset_form,
                informatieobjecttype_formset=informatieobjecttype_formset,
            )
        )
