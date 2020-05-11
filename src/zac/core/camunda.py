from dataclasses import dataclass, field
from itertools import groupby
from typing import List, Optional, Tuple, Type
from xml.etree.ElementTree import Element

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from defusedxml import ElementTree as ET
from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client

from zac.utils.decorators import cache

User = get_user_model()


CAMUNDA_NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "camunda": "http://camunda.org/schema/1.0/bpmn",
}


def _resolve_assignee(username: str) -> User:
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username=username)
    return user


@cache("bpmn:{process_definition_id}", timeout=60 * 60 * 24)
def _get_bpmn(process_definition_id: str) -> ET:
    client = get_client()
    # TODO: cache calls
    bpmn_xml = client.get(f"process-definition/{process_definition_id}/xml")[
        "bpmn20_xml"
    ]

    tree = ET.fromstring(bpmn_xml)
    return tree


def get_zaak_tasks(zaak_url: str) -> List[Task]:
    client = get_client()
    tasks = client.get("task", {"processVariables": f"zaakUrl_eq_{zaak_url}"},)
    tasks = factory(Task, tasks)

    for task in tasks:
        if task.assignee:
            task.assignee = _resolve_assignee(task.assignee)

        task.form = extract_task_form(task)
    return tasks


def complete_task(task_id: str, variables: dict) -> None:
    client = get_client()
    client.post(f"task/{task_id}/complete", json={"variables": variables})


def extract_task_form(task: Task) -> Optional[Type[forms.Form]]:
    tree = _get_bpmn(task.process_definition_id)

    task_id = task.task_definition_key
    task_definition = tree.find(f".//bpmn:userTask[@id='{task_id}']", CAMUNDA_NS)
    formfields = task_definition.findall(".//camunda:formField", CAMUNDA_NS)
    if not formfields:
        return None

    # construct the Form class

    Form = forms.Form
    Form.base_fields = {}

    for definition in formfields:
        name, field = formfield_from_xml(definition)
        Form.base_fields[name] = field

    return Form


FIELD_TYPE_MAP = {
    "enum": forms.ChoiceField,
    "string": forms.CharField,
    "long": forms.IntegerField,
    "boolean": forms.BooleanField,
    "date": forms.DateTimeField,
}


def formfield_from_xml(definition: Element) -> Tuple[str, forms.Field]:
    name = definition.attrib["id"]
    label = definition.attrib.get("label", "")
    default = definition.attrib.get("defaultValue")

    field_type = definition.attrib["type"]
    if field_type not in FIELD_TYPE_MAP:
        raise NotImplementedError(f"Unknown field type '{field_type}'")

    field_class = FIELD_TYPE_MAP[field_type]

    field_kwargs = {
        "label": label,
        "initial": default,
    }

    if field_type == "enum":
        field_kwargs["choices"] = [
            (value.attrib["id"], value.attrib["name"])
            for value in definition.getchildren()
        ]
        field_kwargs["widget"] = forms.RadioSelect

    return name, field_class(required=True, **field_kwargs)


class MessageForm(forms.Form):
    definition_id = forms.CharField(widget=forms.HiddenInput)
    zaak_url = forms.CharField(widget=forms.HiddenInput)
    message = forms.ChoiceField(label=_("Message"), choices=())

    def __init__(self, *args, **kwargs):
        message_names = kwargs.pop("message_names", [])
        super().__init__(*args, **kwargs)
        self.set_message_choices(message_names)

    def set_message_choices(self, message_names: List[str]):
        self.fields["message"].choices = [(name, name) for name in message_names]


@dataclass
class ProcessDefinition:
    id: str
    zaak_url: str
    instance_ids: List[str]
    message_names: List[str] = field(default_factory=list)

    def get_form(self, *args, **kwargs) -> MessageForm:
        kwargs["message_names"] = self.message_names

        initial = kwargs.get("initial", {})
        initial.update(
            {"zaak_url": self.zaak_url, "definition_id": self.id,}
        )

        return MessageForm(initial=initial, *args, **kwargs)


def get_process_definition_messages(zaak_url: str) -> List[ProcessDefinition]:
    """
    Extract the possible messages that can be sent into the process.
    """
    client = get_client()

    instances = client.get("process-instance", {"variables": f"zaakUrl_eq_{zaak_url}"},)

    instances = sorted(instances, key=lambda i: (i["definition_id"], i["id"]))

    defs = [
        ProcessDefinition(
            id=definition_id,
            zaak_url=zaak_url,
            instance_ids=[instance["id"] for instance in instances],
        )
        for definition_id, instances in groupby(
            instances, key=lambda i: i["definition_id"]
        )
    ]

    for definition in defs:
        tree = _get_bpmn(definition.id)
        messages = tree.findall(".//bpmn:message", CAMUNDA_NS)
        definition.message_names = [message.attrib["name"] for message in messages]

    return [definition for definition in defs if definition.message_names]


def send_message(name: str, process_instance_ids: List[str], variables=None) -> None:
    client = get_client()
    for instance_id in process_instance_ids:
        body = {
            "messageName": name,
            "processInstanceId": instance_id,
            "processVariables": variables or {},
        }
        client.post("message", json=body)
