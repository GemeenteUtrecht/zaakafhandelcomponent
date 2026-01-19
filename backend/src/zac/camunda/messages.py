from dataclasses import dataclass, field
from typing import Dict, List

from django.conf import settings

from django_camunda.bpmn import CAMUNDA_NS
from django_camunda.camunda_models import factory
from django_camunda.client import get_client
from django_camunda.types import CamundaId
from zgw_consumers.api_models.base import factory
from zgw_consumers.concurrent import parallel

from zac.camunda.data import ProcessInstance
from zac.core.utils import A_DAY
from zac.utils.decorators import cache

from .bpmn import get_bpmn
from .forms import MessageForm


@dataclass
class DefinitionMessages:
    id: CamundaId
    instance_ids: List[str]
    message_names: List[str] = field(default_factory=list)

    def get_form(self, *args, **kwargs) -> MessageForm:
        kwargs["message_names"] = self.message_names

        initial = kwargs.pop("initial", {})
        initial.update({"definition_id": self.id})

        return MessageForm(initial=initial, *args, **kwargs)


@cache("camunda-messages:{definition_id}", timeout=A_DAY)
def get_messages(definition_id: str, exclude_private=True) -> List[str]:
    tree = get_bpmn(definition_id)
    messages = tree.findall(".//bpmn:message", CAMUNDA_NS)
    if exclude_private:
        return [
            msg.attrib["name"]
            for msg in messages
            if not msg.attrib["name"].startswith("_")
        ]
    else:
        return [msg.attrib["name"] for msg in messages]


@cache("camunda-message:{zaak_url}", timeout=A_DAY)
def get_process_instances_messages_for_zaak(zaak_url: str) -> List[ProcessInstance]:
    payload = {
        "variables": [{"name": "zaakUrl", "operator": "eq", "value": zaak_url}],
        "processDefinitionKeyNotIn": [settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY],
        "rootProcessInstances": True,
    }

    client = get_client()
    url = "process-instance"
    response = client.post(url, json=payload)
    process_instances = [
        factory(ProcessInstance, {**data, "historical": False}) for data in response
    ]
    p_def_ids = list({p.definition_id for p in process_instances})
    def_messages: Dict[str, List[str]] = dict()

    def _get_messages(definition_id: str):
        nonlocal def_messages
        def_messages[definition_id] = get_messages(definition_id)

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        list(executor.map(_get_messages, p_def_ids))

    for p in process_instances:
        p.messages = def_messages.get(p.definition_id, [])

    return process_instances
