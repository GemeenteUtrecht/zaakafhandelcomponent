from typing import Dict, Optional

import requests
from django_camunda.camunda_models import factory
from django_camunda.client import get_client
from django_camunda.types import CamundaId

from zac.utils.decorators import cache

from .data import ProcessInstance


@cache("process-instance:{instance_id}", timeout=2)
def get_process_instance(instance_id: CamundaId) -> Optional[ProcessInstance]:
    client = get_client()
    try:
        data = client.get(f"process-instance/{instance_id}")
    except requests.HTTPError as exc:
        if exc.response.status_code != 404:
            raise

        # check the history
        try:
            data = client.get(f"history/process-instance/{instance_id}")
        except requests.HTTPError as history_exc:
            if history_exc.response.status_code == 404:
                return None
            raise

        data.update(
            {
                "definition_id": data["process_definition_id"],
                "historical": True,
            }
        )
    return factory(ProcessInstance, data)


def delete_process_instance(instance_id: CamundaId, query_params: Dict = dict):
    client = get_client()
    query_params = {
        "skipIoMappings": "true",
    }
    client.delete(f"process-instance/{instance_id}", params=query_params)
