from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from xml.etree.ElementTree import Element

from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import parsers

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


class DynamicFormRenderer(CamelCaseJSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        if response and response.status_code == 400:
            # On validation errors, do not camelize the keys (as they are the form field names)
            return super(CamelCaseJSONRenderer, self).render(
                data,
                accepted_media_type=accepted_media_type,
                renderer_context=renderer_context,
            )
        return super().render(
            data,
            accepted_media_type=accepted_media_type,
            renderer_context=renderer_context,
        )


@register(
    "",
    DynamicFormSerializer,
    DynamicFormWriteSerializer,
    parsers=(parsers.JSONParser,),
    renderers=(DynamicFormRenderer,),
)
def get_context(task: Task) -> DynamicFormContext:
    from ..forms import extract_task_form_fields

    formfields = extract_task_form_fields(task) or []
    form_fields = [get_field_definition(field) for field in formfields]
    return DynamicFormContext(form_fields=form_fields)
