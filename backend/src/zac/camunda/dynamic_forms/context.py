from dataclasses import dataclass
from typing import Any, Dict, List

from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import parsers

from ..data import Task
from ..user_tasks import Context, register
from .serializers import DynamicFormSerializer, DynamicFormWriteSerializer
from .utils import get_field_definition


@dataclass
class DynamicFormContext(Context):
    form_fields: List[Dict[str, Any]]


class DynamicFormRenderer(CamelCaseJSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        if response and divmod(response.status_code, 100)[0] == 4:
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
