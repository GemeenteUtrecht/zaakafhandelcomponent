import logging
from collections import OrderedDict
from typing import Dict, Optional, Union

from django.conf import settings

from django_camunda.client import get_client
from django_camunda.interface import Variable
from django_camunda.utils import serialize_variable
from djangorestframework_camel_case.settings import api_settings
from djangorestframework_camel_case.util import camelize

from zac.camunda.process_instances import (
    delete_process_instance,
    get_process_definitions,
    get_process_instances,
)
from zac.camunda.utils import ordered_dict_to_dict
from zgw.models.zrc import Zaak

logger = logging.getLogger(__name__)


def start_process(
    process_key: Optional[str] = None,
    process_id: Optional[str] = None,
    business_key: Optional[str] = None,
    variables: Dict[str, Union[Variable, dict]] = None,
) -> Dict[str, str]:
    """
    Taken from django_camunda.tasks.start_process - removed shared_task decorator.
    Take care of serialization in this function rather than expecting it to be fed
    camunda variables.

    """
    logger.debug(
        "Received process start: process_key=%s, process_id=%s", process_key, process_id
    )
    if not (process_key or process_id):
        raise ValueError("Provide a process key or process ID")

    client = get_client()
    variables = variables or {}

    # Make sure variable is of type Dict and not OrderedDict as django_camunda can't handle ordereddicts
    _variables = {}
    for key, value in camelize(variables, **api_settings.JSON_UNDERSCOREIZE).items():
        if type(value) is OrderedDict:
            value = ordered_dict_to_dict(value)
        _variables[key] = serialize_variable(value)

    if process_id:
        endpoint = f"process-definition/{process_id}/start"
    else:
        endpoint = f"process-definition/key/{process_key}/start"

    body = {
        "businessKey": business_key or "",
        "withVariablesInReturn": False,
        "variables": _variables,
    }
    response = client.post(endpoint, json=body)

    self_rel = next((link for link in response["links"] if link["rel"] == "self"))
    instance_url = self_rel["href"]

    logger.info("Started process instance %s", response["id"])

    return {"instance_id": response["id"], "instance_url": instance_url}
