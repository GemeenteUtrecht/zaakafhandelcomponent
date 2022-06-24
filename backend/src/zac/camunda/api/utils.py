import logging
from typing import Dict, Optional, Union

from django.conf import settings

from django_camunda.client import get_client
from django_camunda.interface import Variable
from django_camunda.utils import serialize_variable

from zac.camunda.process_instances import delete_process_instance
from zac.camunda.processes import get_process_definitions, get_process_instances
from zac.core.models import CoreConfig
from zgw.models.zrc import Zaak

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
    """
    Taken from django_camunda.tasks.start_process - removed shared_task decorator.

    """
    logger.debug(
        "Received process start: process_key=%s, process_id=%s", process_key, process_id
    )
    if not (process_key or process_id):
        raise ValueError("Provide a process key or process ID")

    client = get_client()
    variables = variables or {}

    _variables = {key: serialize_variable(var) for key, var in variables.items()}

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


def delete_zaak_creation_process(zaak: Zaak) -> None:
    # First check if there is still a CREATE_ZAAK_PROCESS_DEFINITION_KEY process that needs to be cleaned up.
    process_instances = get_process_instances(zaak.url)
    if process_instances:
        process_definitions = {
            pdef.id: pdef
            for pdef in get_process_definitions(
                list(
                    {
                        pi.definition_id
                        for pi in process_instances.values()
                        if pi.definition_id
                    }
                )
            )
        }
        for pi in process_instances.values():
            process_definition = process_definitions.get(pi.definition_id, None)
            if (
                process_definition
                and process_definition.key
                == settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY
            ):
                delete_process_instance(pi.id)
