from defusedxml import ElementTree as ET
from django_camunda.bpmn import get_bpmn as _get_bpmn

from zac.core.utils import A_DAY
from zac.utils.decorators import cache


@cache("bpmn:{process_definition_id}", timeout=A_DAY)
def get_bpmn(process_definition_id: str) -> ET:
    return _get_bpmn(process_definition_id)
