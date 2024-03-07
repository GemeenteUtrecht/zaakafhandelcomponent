from typing import Any, Dict, List, Tuple
from xml.etree.ElementTree import Element

from rest_framework import fields, serializers

from zac.contrib.objects.services import fetch_zaaktypeattributen_objects_for_zaaktype
from zac.core.api.utils import convert_eigenschap_spec_to_json_schema
from zac.core.services import (
    get_catalogi,
    get_eigenschappen_for_zaaktypen,
    get_zaaktypen,
)
from zac.core.utils import A_DAY
from zac.utils.decorators import cache

from ..forms import extract_choices_from_enum_field, extract_properties_from_field
from .data import CamundaFormField
from .validators import maxLengthValidator, minLengthValidator


def get_choices_from_spec(spec: Dict) -> List[Tuple[str, str]]:
    if _enum := spec.get("enum", []):
        return [(choice["label"], choice["value"]) for choice in _enum]
    return []


def get_default_field_kwargs(definition: dict):
    """
    Note: Open Zaak Catalogus only allows ZAAKEIGENSCHAP-values which are
    specified by the EIGENSCHAPSPECIFICATIE of the ZAAKEIGENSCHAP.

    In practice this means there is ALWAYS an upper limit of max. 255 characters.
    There are more validators thinkable based of the EIGENSCHAPSPECIFICATIE but for
    now these 2 validators suffice.

    """
    initial = definition["value"]
    kwargs = {
        "label": definition["label"],
        "initial": initial if initial is not None else fields.empty,
    }
    if spec := definition.get("spec", None):
        validators = []
        if min_length := spec.get("min_length", None):
            validators.append(
                minLengthValidator(
                    min_length=min_length, eigenschap=definition["label"]
                )
            )

        validators.append(
            maxLengthValidator(
                max_length=spec.get("max_length", 255), eigenschap=definition["label"]
            )
        )
        if validators:
            kwargs["validators"] = validators

    return kwargs


def enum_field_kwargs(definition):
    kwargs = get_default_field_kwargs(definition)
    if spec := definition.get("spec"):
        kwargs["choices"] = get_choices_from_spec(spec)

    elif choices := definition.get("enum", None):
        kwargs["choices"] = choices

    return kwargs


FIELD_TYPE_MAP = {
    "enum": (
        serializers.ChoiceField,
        enum_field_kwargs,
    ),
    "string": (
        serializers.CharField,
        get_default_field_kwargs,
    ),
    "int": (
        serializers.IntegerField,
        get_default_field_kwargs,
    ),
    "boolean": (
        serializers.BooleanField,
        get_default_field_kwargs,
    ),
    "date": (
        serializers.DateTimeField,
        get_default_field_kwargs,
    ),
}


INPUT_TYPE_MAP = {
    "enum": "enum",
    "string": "string",
    "long": "int",
    "boolean": "boolean",
    "date": "date",
}


@cache("field:spec:{camunda_field.id}", timeout=A_DAY)
def get_camunda_field_spec(
    camunda_field: CamundaFormField, properties: Dict[str, str]
) -> Dict:
    """
    Note: `spec` is a loose reference to EIGENSCHAPSPECIFICATIE.
    In our implementation certain validation is done by ZaaktypeAttributes as
    well as EIGENSCHAPpen as defined in the Open Zaak Catalogus.

    This ensures we can use camunda generated dynamic form that are still validated
    as specified in the Open Zaak Catalogus or OBJECTS APIs.

    """
    required_ids = ["zaaktypeIdentificatie", "catalogusDomein", "zaakeigenschapNaam"]
    for req_id in required_ids:
        if not properties.get(req_id, False):
            return dict()

    catalogi = {cat.domein: cat for cat in get_catalogi()}
    catalogus = catalogi.get(properties["catalogusDomein"], None)
    if not catalogus:
        return dict()

    zaaktypen = get_zaaktypen(
        catalogus=catalogus.url, identificatie=properties["zaaktypeIdentificatie"]
    )
    if not zaaktypen:
        return dict()

    else:
        zaaktype = zaaktypen[0]
    zaak_attributes = {
        zatr["naam"]: zatr
        for zatr in fetch_zaaktypeattributen_objects_for_zaaktype(zaaktype=zaaktype)
    }
    eigenschappen = {ei.naam: ei for ei in get_eigenschappen_for_zaaktypen(zaaktypen)}
    if not (eigenschap := eigenschappen.get(properties["zaakeigenschapNaam"], None)):
        return dict()

    if (zatr := zaak_attributes.get(eigenschap.naam)) and (enum := zatr.get("enum")):
        eigenschap.specificatie.waardenverzameling = enum

    return convert_eigenschap_spec_to_json_schema(eigenschap.specificatie)


def get_field_definition(field: Element) -> Dict[str, Any]:
    """
    Note: Camunda form fields that are choice based should be defined as `string`
    if the ENUM is defined by the EIGENSCHAPSPECIFICATIE or ZaaktypeAttribute.
    If this is case, the field_type `string` will be seen as `enum` instead
    so as to enforce proper validation from rest_framework serializers.

    """
    field_definition = {
        "name": field.attrib["id"],
        "label": field.attrib.get("label", field.attrib["id"]),
        "value": field.attrib.get("defaultValue"),
    }

    camunda_field = CamundaFormField(element=field)
    if properties := extract_properties_from_field(camunda_field):
        if properties.get("validateZaakeigenschap", "0") == "1":
            field_definition["spec"] = get_camunda_field_spec(camunda_field, properties)

    choices = []
    if spec := field_definition.get("spec"):
        choices = get_choices_from_spec(spec)
    else:
        choices = extract_choices_from_enum_field(camunda_field)
    if choices:
        field_definition["enum"] = choices
        field_definition["input_type"] = INPUT_TYPE_MAP["enum"]
    else:
        if (field_type := field.attrib["type"]) not in INPUT_TYPE_MAP:
            raise NotImplementedError(f"Unknown field type '{field_type}'")
        field_definition["input_type"] = INPUT_TYPE_MAP[field_type]

    if not field_definition.get("spec"):
        field_definition["spec"] = None

    return field_definition
