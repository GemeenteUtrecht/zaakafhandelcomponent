from typing import List, Optional, Tuple

from django.utils.translation import ugettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from rest_framework import serializers
from zgw_consumers.api_models.catalogi import InformatieObjectType

from ..services import fetch_zaaktype, get_informatieobjecttypen_for_zaaktype, get_zaak


def get_informatieobjecttypen_for_zaak(url: str) -> List[InformatieObjectType]:
    zaak = get_zaak(zaak_url=url)
    zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)
    informatieobjecttypen = get_informatieobjecttypen_for_zaaktype(zaak.zaaktype)
    return informatieobjecttypen


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
                _(f"Error: Verwachtte een list maar kreeg {type(data).__name__}.")
            )
        data = ",".join(data)
        return data

    def to_internal_value(self, data):
        if not isinstance(data, str):
            raise serializers.ValidationError(
                _(f"Error: Verwachtte een str maar kreeg {type(data).__name__}.")
            )

        if not data and self.required:
            raise serializers.ValidationError(
                _("Error: Dit veld is verplicht en mag niet leeg zijn.")
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
                        f"Error: Dit veld bevatte: {invalid_choices_string}, maar mag alleen een (sub)set zijn van: {valid_choices_string}."
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
        json_schema.update({"min_length": 1, "max_length": int(spec.lengte)})

    if spec.waardenverzameling:
        json_schema.update({"enum": spec.waardenverzameling})

    return json_schema
