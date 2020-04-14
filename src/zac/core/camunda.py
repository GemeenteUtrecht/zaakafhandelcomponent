from typing import List, Optional, Tuple, Type
from xml.etree.ElementTree import Element

from django import forms
from django.contrib.auth import get_user_model

from defusedxml import ElementTree as ET
from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client

User = get_user_model()


def _resolve_assignee(username: str) -> User:
    user = User.objects.get(username=username)
    return user


def get_zaak_tasks(zaak_url: str) -> List[Task]:
    client = get_client()
    tasks = client.get("task", {"processVariables": f"zaakUrl_eq_{zaak_url}"},)
    tasks = factory(Task, tasks)

    for task in tasks:
        if task.assignee:
            task.assignee = _resolve_assignee(task.assignee)

        task._form = extract_task_form(task)
    return tasks


def complete_task(task_id: str, variables: dict) -> None:
    client = get_client()
    client.post(f"task/{task_id}/complete", json={"variables": variables})


def extract_task_form(task: Task) -> Optional[Type[forms.Form]]:
    ns = {
        "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "camunda": "http://camunda.org/schema/1.0/bpmn",
    }

    client = get_client()
    # TODO: cache calls
    bpmn_xml = client.get(f"process-definition/{task.process_definition_id}/xml")[
        "bpmn20_xml"
    ]

    tree = ET.fromstring(bpmn_xml)
    task_id = task.task_definition_key
    task_definition = tree.find(f".//bpmn:userTask[@id='{task_id}']", ns)
    formfields = task_definition.findall(".//camunda:formField", ns)
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
    label = definition.attrib["label"]
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

    return name, field_class(required=True, **field_kwargs)
