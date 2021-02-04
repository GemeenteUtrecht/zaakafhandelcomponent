from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from ..user_tasks import usertask_context_serializer

FIELD_TYPE_MAP = {
    "enum": serializers.ChoiceField,
    "string": serializers.CharField,
    "long": serializers.IntegerField,
    "boolean": serializers.BooleanField,
    "date": serializers.DateTimeField,
}


INPUT_TYPE_MAP = {
    "enum": "enum",
    "string": "string",
    "long": "int",
    "boolean": "boolean",
    "date": "date",
}


class EnumField(serializers.ListField):
    child = serializers.ListField(
        label=_("Possible enum choice"),
        help_text=_("First element is the value, second element is the label."),
        min_length=2,
        max_length=2,
    )


class FormFieldSerializer(serializers.Serializer):
    name = serializers.CharField(
        label=_("Field name/identifier"),
        required=True,
    )
    title = serializers.CharField(
        label=_("Field label"),
        help_text=_(
            "Human-readable field title. Defaults to `name` property if not provided."
        ),
        required=True,
    )
    input_type = serializers.ChoiceField(
        label=_("Input data type"),
        choices=list(INPUT_TYPE_MAP.values()),
        required=True,
    )
    value = serializers.Field(
        label=_("Field value"),
        help_text=_("Current or default value"),
        allow_null=True,
    )
    enum = EnumField(
        label=_("Possible enum choices"),
        help_text=_("Type varies with the input type."),
        allow_null=True,
    )


@usertask_context_serializer
class DynamicFormSerializer(serializers.Serializer):
    form_fields = FormFieldSerializer(many=True, read_only=True)
