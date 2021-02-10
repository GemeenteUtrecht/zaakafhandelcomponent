from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from xml.etree.ElementTree import Element

from ..data import Task
from ..user_tasks import Context, register
from .serializers import (
    FIELD_TYPE_MAP,
    INPUT_TYPE_MAP,
    DynamicFormSerializer,
    DynamicFormWriteSerializer,
)


@dataclass
class DynamicFormContext(Context):
    form_fields: List[Dict[str, Any]]


def get_choice(value: Element) -> Tuple[str, str]:
    val = value.attrib["id"]
    label = value.attrib.get("name", val)
    return (val, label)


def get_field_definition(field: Element) -> Dict[str, Any]:
    field_id = field.attrib["id"]
    default = field.attrib.get("defaultValue")
    field_type = field.attrib["type"]
    if field_type not in FIELD_TYPE_MAP:
        raise NotImplementedError(f"Unknown field type '{field_type}'")

    input_type = INPUT_TYPE_MAP[field_type]

    field_definition = {
        "name": field_id,
        "label": field.attrib.get("label", field_id),
        "input_type": input_type,
        "value": default,
    }

    if field_type == "enum":
        choices = [get_choice(value) for value in field.getchildren()]
        field_definition["enum"] = choices

    return field_definition


@register("", DynamicFormSerializer, DynamicFormWriteSerializer)
def get_context(task: Task) -> DynamicFormContext:
    from ..forms import extract_task_form_fields

    formfields = extract_task_form_fields(task) or []
    form_fields = [get_field_definition(field) for field in formfields]
    return DynamicFormContext(form_fields=form_fields)


def build_dynamic_form_serializer(task: Task, **kwargs) -> DynamicFormWriteSerializer:
    from ..forms import extract_task_form_fields

    formfields = extract_task_form_fields(task) or []

    fields = {}
    for field in formfields:
        field_type = field.attrib["type"]
        field_definition = get_field_definition(field)
        field_cls, get_kwargs = FIELD_TYPE_MAP[field_type]
        name = field_definition.pop("name")
        fields[name] = field_cls(**get_kwargs(field_definition))

    Serializer = type(
        "DynamicFormWriteSerializer", (DynamicFormWriteSerializer,), fields
    )

    return Serializer(**kwargs)
