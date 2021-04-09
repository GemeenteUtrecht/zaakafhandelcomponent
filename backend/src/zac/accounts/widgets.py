from django import forms

from .permissions import registry


class CheckboxSelectMultipleWithLinks(forms.CheckboxSelectMultiple):
    option_template_name = (
        "admin/accounts/widgets/checkbox_option_with_link.html"
    )

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        model = self.choices.queryset.model
        context.update({"opts": model._meta})
        return context


class PolicyWidget(forms.Widget):
    template_name = "admin/accounts/widgets/policy_editor.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        json_schemas = {
            name: permission.blueprint_class.display_as_jsonschema()
            for name, permission in registry.items()
        }
        context.update({"json_schemas": json_schemas})
        return context
