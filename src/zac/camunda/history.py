from typing import Any

from django_camunda.client import get_client
from django_camunda.types import CamundaId
from django_camunda.utils import deserialize_variable


def get_historical_variable(instance_id: CamundaId, name: str) -> Any:
    client = get_client()

    response = client.get(
        "history/variable-instance",
        {
            "processInstanceId": instance_id,
            "variableName": name,
            "deserializeValues": "false",
        },
    )
    values = sorted(response, key=lambda val: val["create_time"], reverse=True)
    return deserialize_variable(values[0])
