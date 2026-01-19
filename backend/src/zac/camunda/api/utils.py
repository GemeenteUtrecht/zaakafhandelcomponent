from typing import Dict, Optional

from django_camunda.client import get_client
from django_camunda.types import CamundaId

from zac.core.models import CoreConfig


def get_incidents_for_process_instance(pid: CamundaId) -> list[Optional[Dict]]:
    client = get_client()
    incidents = client.get(f"incident?processInstanceId={pid}")
    return incidents


def get_bptl_app_id_variable() -> Dict[str, str]:
    """
    Get the name and value of the bptl app ID variable for BPTL.
    """
    core_config = CoreConfig.get_solo()
    return {
        "bptlAppId": core_config.app_id,
    }
