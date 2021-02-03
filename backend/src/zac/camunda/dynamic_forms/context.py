from typing import List, Optional
from xml.etree.ElementTree import Element

from django_camunda.bpmn import CAMUNDA_NS

from zac.core.camunda import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_zaak

from ..bpmn import get_bpmn
from ..data import Task
from ..process_instances import get_process_instance
from ..user_tasks.context import register
from .data import DynamicFormContext, FormField
from .form_field import get_form_field_context
from .serializers import DynamicFormContextSerializer


def get_form_fields_from_task(task) -> Optional[List[Element]]:
    """
    Retrieve form fields from camunda task.
    """
    tree = get_bpmn(task.process_definition_id)
    task_id = task.task_definition_key
    task_definition = tree.find(f".//bpmn:userTask[@id='{task_id}']", CAMUNDA_NS)
    form_fields = task_definition.findall(".//camunda:formField", CAMUNDA_NS)
    return form_fields


def get_form_fields(task_form_fields) -> Optional[List[FormField]]:
    form_fields = []
    for definition in task_form_fields or []:
        input_type = definition.attrib["type"]
        default = definition.attrib.get("defaultValue")
        kwargs = {"value": default}
        if input_type == "enum":
            kwargs["choices"] = [
                (value.attrib["id"], value.attrib["name"])
                for value in definition.getchildren()
            ]

        form_fields.append(
            FormField(
                name=definition.attrib["id"],
                label=definition.attrib.get("label", ""),
                input_type=input_type,
                form_field_context=get_form_field_context(input_type, **kwargs),
            )
        )
    return form_fields


@register("zac:dynamicForm", DynamicFormContextSerializer)
def get_context(task: Task) -> DynamicFormContext:
    # TODO: Write tests.

    # Get zaak and construct title
    process_instance = get_process_instance(task.process_instance_id)
    zaak_url = get_process_zaak_url(process_instance)
    zaak = get_zaak(zaak_url=zaak_url)
    zaaktype = fetch_zaaktype(zaak.zaaktype)
    title = f"{zaaktype.omschrijving} - {zaaktype.versiedatum}"

    task_form_fields = get_form_fields_from_task(task)
    form_fields = get_form_fields(task_form_fields)

    return DynamicFormContext(
        title=title,
        zaak_informatie=zaak,
        form_fields=form_fields,
    )
