from defusedxml import ElementTree as ET
from django_camunda.bpmn import get_bpmn as _get_bpmn

from zac.utils.decorators import cache


@cache("bpmn:{process_definition_id}", timeout=60 * 60 * 24)
def get_bpmn(process_definition_id: str) -> ET:
    return _get_bpmn(process_definition_id)
