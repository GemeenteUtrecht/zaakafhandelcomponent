from defusedxml import ElementTree as ET
from django_camunda.bpmn import get_bpmn as _get_bpmn

from zac.utils.decorators import cache

A_DAY = 60 * 60 * 24


@cache("bpmn:{process_definition_id}", timeout=A_DAY)
def get_bpmn(process_definition_id: str) -> ET:
    return _get_bpmn(process_definition_id)
