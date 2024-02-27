from typing import Any, Dict, List, Optional, Tuple
from xml.etree.ElementTree import Element

from django import forms
from django.utils.translation import gettext_lazy as _

from django_camunda.bpmn import CAMUNDA_NS
from django_camunda.camunda_models import Task

from zac.core.utils import A_DAY
from zac.utils.decorators import cache

from .bpmn import get_bpmn
from .dynamic_forms.data import CamundaFormField
from .user_tasks.context import REGISTRY


@cache("camundaField:choices:{field.id}", timeout=A_DAY)
def extract_choices_from_enum_field(field: CamundaFormField) -> List[Tuple[str, str]]:
    values = field.element.findall(".//camunda:value", CAMUNDA_NS)
    return [
        (value.attrib.get("id"), value.attrib.get("name", value.attrib["id"]))
        for value in values
        if value.attrib.get("id")
    ]


@cache("camundaField:constraints:{field.id}", timeout=A_DAY)
def extract_constraint_from_field(field: CamundaFormField):
    return field.element.findall(".//camunda:constraint", CAMUNDA_NS)


@cache("camundaField:props:{field.id}", timeout=A_DAY)
def extract_properties_from_field(field: CamundaFormField) -> Dict[str, str]:
    return {
        prop.attrib.get("id", ""): prop.attrib.get("value", "")
        for prop in field.element.findall(".//camunda:property", CAMUNDA_NS)
        if prop.attrib.get("id", "")
    }


def extract_task_form_fields(task: Task) -> Optional[List[Element]]:
    """
    Get the Camunda form fields definition from the BPMN definition.

    Camunda embeds form fields as an extension into the BPMN definition. We can extract
    these and map them to form or serializer fields.
    """
    if task.form_key and task.form_key in REGISTRY:
        return None

    tree = get_bpmn(task.process_definition_id)

    task_id = task.task_definition_key
    task_definition = tree.find(f".//bpmn:userTask[@id='{task_id}']", CAMUNDA_NS)
    formfields = task_definition.findall(".//camunda:formField", CAMUNDA_NS)
    if not formfields:
        return None

    return formfields


def extract_task_form_key(task: Task) -> str:
    """
    Get the Camunda form key of a user task from the BPMN definition.

    Camunda embeds the form key as an attribute into the BPMN definition.
    """

    tree = get_bpmn(task.process_definition_id)

    task_id = task.task_definition_key
    task_definition = tree.find(f".//bpmn:userTask[@id='{task_id}']", CAMUNDA_NS)
    form_key = task_definition.attrib.get(
        "{" + CAMUNDA_NS["camunda"] + "}formKey", None
    )
    return form_key


def extract_task_form(task: Task, form_key_mapping: dict) -> bool:
    return form_key_mapping.get(task.form_key)


class MessageForm(forms.Form):
    process_instance_id = forms.CharField(widget=forms.HiddenInput)
    message = forms.ChoiceField(label=_("Message"), choices=())

    def __init__(self, *args, **kwargs):
        message_names = kwargs.pop("message_names", [])
        super().__init__(*args, **kwargs)
        self.set_message_choices(message_names)

    def set_message_choices(self, message_names: List[str]):
        self.fields["message"].choices = [(name, name) for name in message_names]


class TaskFormMixin:
    """
    Define a base class for forms driven by a particular form key in Camunda.

    The form expects a :class:`Task` instance as param, which subclasses can use to
    retrieve related information.
    """

    def __init__(self, task: Task, *args, **kwargs):
        self.task = task
        super().__init__(*args, **kwargs)

    def set_context(self, context: dict):
        self.context = context

    def on_submission(self):
        """
        Hook for forms that do need to persist data.
        """
        pass

    def get_process_variables(self) -> Dict[str, Any]:
        assert self.is_valid(), "Form does not pass validation"
        return self.cleaned_data


def get_form_data(form: forms.Form) -> Dict[str, Dict]:
    """
    Serialize the form data and errors for the frontend.
    """
    errors = (
        {
            field: [{"msg": next(iter(error)), "code": error.code} for error in _errors]
            for field, _errors in form.errors.as_data().items()
        }
        if form.is_bound
        else {}
    )

    values = {field.name: field.value() for field in form}
    return {
        "errors": errors,
        "values": values,
    }


class TaskFormSetMixin:
    """
    Define a base class for formsets driven by a particular form key in Camunda.
    """

    def __init__(self, task: Task, *args, **kwargs):
        self.task = task
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def on_submission(self, form=None):
        """
        Hook for forms that do need to persist data.
        """
        pass

    def get_process_variables(self) -> Dict[str, Any]:
        raise NotImplementedError

    @property
    def form_data(self) -> List[Dict[str, Any]]:
        return [get_form_data(form) for form in self]


class BaseTaskFormSet(TaskFormSetMixin, forms.BaseFormSet):
    pass


class DummyForm(TaskFormMixin, forms.Form):
    pass
