from typing import Dict

from django.utils.translation import gettext_lazy as _

from rest_framework import fields, serializers
from rest_framework.utils.serializer_helpers import BindingDict

from zac.api.polymorphism import PolymorphicSerializer
from zac.core.api.serializers import EigenschapSpecificatieJsonSerializer

from ..data import Task
from ..user_tasks import usertask_context_serializer
from .utils import FIELD_TYPE_MAP, INPUT_TYPE_MAP


class EnumField(serializers.ListField):
    child = serializers.ListField(
        child=serializers.CharField(),
        label=_("Possible enum choice"),
        help_text=_("First element is the value, second element is the label."),
        min_length=2,
        max_length=2,
    )


VALUE_DEFAULTS = {
    "label": _("Field value"),
    "help_text": _("Current or default value."),
    "allow_null": True,
}


class StringSerializer(serializers.Serializer):
    value = serializers.CharField(**VALUE_DEFAULTS)


class EnumSerializer(StringSerializer):
    enum = EnumField(
        label=_("Possible enum choices"),
        required=True,
    )


class IntSerializer(serializers.Serializer):
    value = serializers.IntegerField(**VALUE_DEFAULTS)


class BooleanSerializer(serializers.Serializer):
    value = serializers.BooleanField(**VALUE_DEFAULTS)


class DatetimeSerializer(serializers.Serializer):
    value = serializers.DateTimeField(**VALUE_DEFAULTS)


class FormFieldSerializer(PolymorphicSerializer):
    discriminator_field = "input_type"
    serializer_mapping = {
        "enum": EnumSerializer,
        "string": StringSerializer,
        "int": IntSerializer,
        "boolean": BooleanSerializer,
        "date": DatetimeSerializer,
    }

    name = serializers.CharField(
        label=_("Field name/identifier"),
        required=True,
    )
    label = serializers.CharField(
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
    spec = EigenschapSpecificatieJsonSerializer(required=False, allow_null=True)


@usertask_context_serializer
class DynamicFormSerializer(serializers.Serializer):
    form_fields = FormFieldSerializer(many=True, read_only=True)


# Write serializers


def get_dynamic_form_serializer_fields(task: Task) -> Dict[str, fields.Field]:
    from ..forms import extract_task_form_fields
    from .context import get_field_definition

    formfields = extract_task_form_fields(task) or []

    fields = {}
    for field in formfields:
        field_definition = get_field_definition(field)
        field_cls, get_kwargs = FIELD_TYPE_MAP[field_definition["input_type"]]
        name = field_definition.pop("name")
        fields[name] = field_cls(**get_kwargs(field_definition))

    return fields


class DynamicFormWriteSerializer(serializers.Serializer):
    def __new__(cls, *args, **kwargs):
        """
        Inject the derived serializer fields from the task form definition.
        """
        serializer = super().__new__(cls, *args, **kwargs)

        if "context" not in kwargs or "task" not in kwargs["context"]:
            return serializer

        task = kwargs["context"]["task"]
        fields = BindingDict(serializer)
        for key, value in get_dynamic_form_serializer_fields(task).items():
            fields[key] = value
        serializer.fields = fields

        return serializer

    def on_submission(self):
        pass

    def get_process_variables(self):
        return self.validated_data
