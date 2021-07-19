from typing import Any, Dict, List, Optional
from xml.etree.ElementTree import Element

from django import forms
from django.utils.translation import gettext_lazy as _

from django_camunda.bpmn import CAMUNDA_NS
from django_camunda.camunda_models import Task

from .bpmn import get_bpmn
from .user_tasks.context import REGISTRY


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


def extract_task_form(task: Task, form_key_mapping: dict) -> bool:
    return form_key_mapping.get(task.form_key)
