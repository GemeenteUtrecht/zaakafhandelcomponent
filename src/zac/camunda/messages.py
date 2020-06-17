from dataclasses import dataclass, field
from itertools import groupby
from typing import List

from django_camunda.bpmn import CAMUNDA_NS
from django_camunda.client import get_client
from django_camunda.types import CamundaId

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


def get_process_definition_messages(zaak_url: str) -> List[DefinitionMessages]:
    """
    Extract the possible messages that can be sent into the process.
    """
    client = get_client()

    instances = client.get("process-instance", {"variables": f"zaakUrl_eq_{zaak_url}"},)

    instances = sorted(instances, key=lambda i: (i["definition_id"], i["id"]))

    defs = [
        DefinitionMessages(
            id=definition_id, instance_ids=[instance["id"] for instance in instances],
        )
        for definition_id, instances in groupby(
            instances, key=lambda i: i["definition_id"]
        )
    ]

    for definition in defs:
        tree = get_bpmn(definition.id)
        messages = tree.findall(".//bpmn:message", CAMUNDA_NS)
        definition.message_names = [message.attrib["name"] for message in messages]

    return [definition for definition in defs if definition.message_names]
