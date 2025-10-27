from typing import Optional, Tuple

from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from rest_framework import serializers


class ValidFieldChoices(DjangoChoices):
    geboortedatum = ChoiceItem("geboorte.datum")
    geboorteland = ChoiceItem("geboorte.land")
    kinderen = ChoiceItem("kinderen")
    partners = ChoiceItem("partners")
    verblijfplaats = ChoiceItem("verblijfplaats")


class ValidExpandChoices(DjangoChoices):
    kinderen = ChoiceItem("kinderen")
    partners = ChoiceItem("partners")


class CSMultipleChoiceField(serializers.Field):
    def __init__(
        self,
        *args,
        choices: Optional[Tuple] = (),
        required: Optional[bool] = False,
        strict: Optional[bool] = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.choices = choices
        self.required = required
        self.strict = strict

    def to_representation(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError(
                _("Error: expected a `list` but received `{datatype}`.").format(
                    datatype=type(data).__name__
                )
            )
        data = ",".join(data)
        return data

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError(
                _("Error: expected a `str` but received `{datatype}`.").format(
                    datatype=type(data).__name__
                )
            )

        if not data and self.required:
            raise serializers.ValidationError(
                _("Error: this field is required and cannot be empty.")
            )

        values = data.split(",")

        if self.choices:
            is_subset = [
                any(value in choice_tuple for choice_tuple in self.choices)
                for value in values
            ]
            if self.strict and not all(is_subset):
                invalid_choices_string = ",".join(
                    [value for value, valid in zip(values, is_subset) if not valid]
                )
                valid_choices_string = ", ".join([choice for choice, _ in self.choices])
                raise serializers.ValidationError(
                    _(
                        "Error: this field contained: {invalid_choices_string}, but can only be a subset of: {valid_choices_string}."
                    ).format(
                        invalid_choices_string=invalid_choices_string,
                        valid_choices_string=valid_choices_string,
                    )
                )
            else:
                subset = [value for value, valid in zip(values, is_subset) if valid]
                values = subset.copy()

        return values


class TypeChoices(DjangoChoices):
    string = ChoiceItem("string")
    number = ChoiceItem("number")


EIGENSCHAP_FORMAT_TYPE_MAPPING = {
    "tekst": {"type": TypeChoices.string},
    "getal": {"type": TypeChoices.number},
    "datum": {"type": TypeChoices.string, "format": "date"},
    "datum_tijd": {"type": TypeChoices.string, "format": "date-time"},
}


def convert_eigenschap_spec_to_json_schema(spec) -> dict:
    json_schema = EIGENSCHAP_FORMAT_TYPE_MAPPING[spec.formaat].copy()

    if spec.formaat == "tekst":
        tekst_schema = {"min_length": 1, "max_length": int(spec.lengte)}
        if int(spec.lengte) > 254:
            tekst_schema["format"] = "long"
        json_schema.update(tekst_schema)

    if spec.waardenverzameling:
        waardenverzameling = []
        for opt in spec.waardenverzameling:
            if type(opt) in [list, tuple] and len(opt) == 2:
                waarde = {"label": opt[0], "value": opt[1]}
            else:
                waarde = {"label": opt, "value": opt}
            waardenverzameling.append(waarde)
        json_schema.update({"enum": waardenverzameling})

    return json_schema
