from typing import Dict, List, Optional

from django_camunda.client import get_client

from zac.camunda.client import CAMUNDA_CLIENT_CLASS


def get_camunda_variable_instances(
    request_body: Dict, client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> List[Dict]:
    if not request_body:
        return []

    if not client:
        client = get_client()

    return client.post(
        "variable-instance",
        json=request_body,
    )
