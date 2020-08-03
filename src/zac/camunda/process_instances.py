from dataclasses import dataclass
from typing import Optional

import requests
from django_camunda.camunda_models import Model, factory
from django_camunda.client import get_client
from django_camunda.types import CamundaId


@dataclass
class ProcessInstance(Model):
    id: str
    definition_id: str
    business_key: str
    case_instance_id: str
    suspended: bool
    tenant_id: str


def get_process_instance(instance_id: CamundaId) -> Optional[ProcessInstance]:
    client = get_client()
    try:
        data = client.get(f"process-instance/{instance_id}")
    except requests.HTTPError as exc:
        if exc.response.status_code == 404:
            return None
        raise
    return factory(ProcessInstance, data)
