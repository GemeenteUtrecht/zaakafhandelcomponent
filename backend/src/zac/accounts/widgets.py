from django import forms

from .permissions import object_type_registry


class PolicyWidget(forms.Widget):
    template_name = "admin/accounts/widgets/policy_editor.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        json_schemas = {
            object_type_name: object_type.blueprint_class.display_as_jsonschema()
            for object_type_name, object_type in object_type_registry.items()
        }
        context.update({"json_schemas": json_schemas})
        return context
