from django import forms

from .models import PermissionSet


class PermissionSetForm(forms.ModelForm):
    class Meta:
        model = PermissionSet
        fields = (
            "name",
            "description",
            "permissions",
            "catalogus",
            "zaaktype_identificaties",
            "max_va",
        )
        widgets = {
            "max_va": forms.RadioSelect,
        }
