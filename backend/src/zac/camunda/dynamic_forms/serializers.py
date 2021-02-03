from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.polymorphism import PolymorphicSerializer

from ..api.serializers import TaskZaakInformatieSerializer
from ..user_tasks.context import usertask_context_serializer
from .data import (
    BooleanField,
    ChoiceField,
    DateTimeField,
    DynamicFormContext,
    FormFieldContext,
    IntField,
    StringField,
)
from .drf import form_field_context_serializer
from .form_field import REGISTRY_INPUT_TYPES, register_input_type


class DynamicFormFieldSerializer(PolymorphicSerializer):
    discriminator_field = "input_type"
    serializer_mapping = {}  # set at run-time based on the REGISTRY

    input_type = serializers.ChoiceField(
        label=_("Input type for form field"),
        source="formfield.input_type",
        help_text=_(
            "The input type of the form field to render. Note that unknown input type keys (= not "
            "present in the enum) will be returned as is."
        ),
        allow_blank=True,
        choices=(),
    )

    name = serializers.CharField()
    label = serializers.CharField()
    # the form_field_context is added by the serializer_mapping serializers

    def __init__(self, *args, **kwargs):

        self.serializer_mapping = {
            form_key: serializer
            for form_key, (callback, serializer) in REGISTRY_INPUT_TYPES.items()
        }

        super().__init__(*args, **kwargs)

        self.fields["input_type"].choices = list(REGISTRY_INPUT_TYPES.keys())


@usertask_context_serializer
class DynamicFormContextSerializer(APIModelSerializer):
    """
    TODO: Write tests
    """

    title = serializers.CharField()
    zaak_informatie = TaskZaakInformatieSerializer(label=_("Case summary"))
    # form_fields = DynamicFormFieldSerializer(many=True)

    class Meta:
        model = DynamicFormContext
        fields = (
            "title",
            "zaak_informatie",
            # "form_fields",
        )


@form_field_context_serializer
class BooleanFieldSerializer(APIModelSerializer):
    class Meta:
        model = BooleanField
        fields = ("value",)


@form_field_context_serializer
class DateTimeFieldSerializer(APIModelSerializer):
    class Meta:
        model = DateTimeField
        fields = ("value",)


@form_field_context_serializer
class IntFieldSerializer(APIModelSerializer):
    class Meta:
        model = IntField
        fields = ("value",)


@form_field_context_serializer
class StringFieldSerializer(APIModelSerializer):
    class Meta:
        model = StringField
        fields = ("value",)


@form_field_context_serializer
class ChoiceFieldContextSerializer(APIModelSerializer):
    class Meta:
        model = ChoiceField
        fields = (
            "value",
            "choices",
        )


INPUT_TYPE_FIELD_MAPPING = {
    "boolean": BooleanField,
    "date": DateTimeField,
    "long": IntField,
    "string": StringField,
    "enum": ChoiceField,
}


@register_input_type("zac:form_field:boolean", BooleanFieldSerializer)
@register_input_type("zac:form_field:date", DateTimeFieldSerializer)
@register_input_type("zac:form_field:long", IntFieldSerializer)
@register_input_type("zac:form_field:string", StringFieldSerializer)
@register_input_type("zac:form_field:enum", ChoiceFieldContextSerializer)
def get_form_field_context(input_type: str, **kwargs):
    return INPUT_TYPE_FIELD_MAPPING[input_type](**kwargs)
