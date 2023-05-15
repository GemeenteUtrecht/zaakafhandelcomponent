from dataclasses import dataclass, field
from typing import List

from django_camunda.bpmn import CAMUNDA_NS
from django_camunda.types import CamundaId

from zac.utils.decorators import cache

from .bpmn import get_bpmn
from .forms import MessageForm

A_DAY = 24 * 60 * 60


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
def get_messages(definition_id: str) -> List[str]:
    tree = get_bpmn(definition_id)
    messages = tree.findall(".//bpmn:message", CAMUNDA_NS)

    return [message.attrib["name"] for message in messages]
