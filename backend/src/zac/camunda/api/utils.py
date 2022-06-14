import logging
from typing import Dict, Optional, Union

from django_camunda.client import get_client
from django_camunda.interface import Variable

from zac.core.models import CoreConfig

logger = logging.getLogger(__name__)


def get_bptl_app_id_variable() -> Dict[str, str]:
    """
    Get the name and value of the bptl app ID variable for BPTL.
    """
    core_config = CoreConfig.get_solo()
    return {
        "bptlAppId": core_config.app_id,
    }


def start_process(
    process_key: Optional[str] = None,
    process_id: Optional[str] = None,
    business_key: Optional[str] = None,
    variables: Dict[str, Union[Variable, dict]] = None,
) -> Dict[str, str]:
    logger.debug(
        "Received process start: process_key=%s, process_id=%s", process_key, process_id
    )
    if not (process_key or process_id):
        raise ValueError("Provide a process key or process ID")

    client = get_client()
    variables = variables or {}

    _variables = {
        key: var.serialize() if isinstance(var, Variable) else var
        for key, var in variables.items()
    }

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
