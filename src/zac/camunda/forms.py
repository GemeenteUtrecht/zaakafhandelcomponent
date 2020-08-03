from typing import Any, Dict, List, Optional, Type

from django import forms
from django.utils.translation import gettext_lazy as _

from django_camunda.bpmn import CAMUNDA_NS
from django_camunda.camunda_models import Task
from django_camunda.forms import formfield_from_xml

from .bpmn import get_bpmn


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


class DummyForm(TaskFormMixin, forms.Form):
    pass


def extract_task_form(
    task: Task, form_key_mapping: dict
) -> Optional[Dict[str, Type[TaskFormMixin]]]:
    if task.form_key in form_key_mapping:
        return form_key_mapping[task.form_key]

    tree = get_bpmn(task.process_definition_id)

    task_id = task.task_definition_key
    task_definition = tree.find(f".//bpmn:userTask[@id='{task_id}']", CAMUNDA_NS)
    formfields = task_definition.findall(".//camunda:formField", CAMUNDA_NS)
    if not formfields:
        return None

    # construct the Form class

    _fields = {}
    for definition in formfields:
        name, field = formfield_from_xml(definition)
        _fields[name] = field

    return {"form": type("Form", (TaskFormMixin, forms.Form), _fields)}
