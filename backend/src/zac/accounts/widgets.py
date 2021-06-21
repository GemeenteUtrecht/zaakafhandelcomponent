from django import forms

from .permissions import registry


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
