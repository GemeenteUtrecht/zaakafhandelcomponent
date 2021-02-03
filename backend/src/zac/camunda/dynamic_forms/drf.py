from django.utils.translation import gettext_lazy as _

from rest_framework.utils import formatting
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.polymorphism import SerializerCls


def form_field_context_serializer(serializer_cls: SerializerCls) -> SerializerCls:
    """
    Ensure that the FormFieldContext-specific serializer is wrapped in a FormField serializer.

    The decorator enforces the same label/help_text and meta-information for the API
    schema documentation.
    """
    from .data import FormField

    name = serializer_cls.__name__
    name = formatting.remove_trailing_string(name, "Serializer")
    name = formatting.remove_trailing_string(name, "Field")

    class FormFieldSerializer(APIModelSerializer):
        form_field_context = serializer_cls(
            label=_("Form Field Context"),
            help_text=_(
                "The form field shape depends on the `input_type` property. The value will be "
                "`null` if the backend does not 'know' the form field `input_type`."
            ),
            allow_null=True,
        )

        class Meta:
            model = FormField
            fields = ("form_field_context",)

    name = f"{name}FormFieldSerializer"
    return type(name, (FormFieldSerializer,), {})
