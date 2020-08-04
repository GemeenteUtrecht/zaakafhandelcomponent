from dataclasses import dataclass, field
from typing import Any

from django.urls import reverse

from django_camunda.api import get_process_instance_variable, get_task_variable
from django_camunda.camunda_models import Model, Task as _Task
from django_camunda.types import CamundaId


@dataclass
class ProcessInstance(Model):
    id: CamundaId
    definition_id: str
    business_key: str = ""
    case_instance_id: str = ""
    suspended: bool = False
    tenant_id: str = ""

    definition: str = None
    sub_processes: list = field(default_factory=list)
    parent_process: str = None
    messages: list = field(default_factory=list)
    tasks: list = field(default_factory=list)

    def get_variable(self, name: str) -> Any:
        return get_process_instance_variable(self.id, name)

    def title(self) -> str:
        return self.definition.name or self.definition.key


@dataclass
class Task(_Task):
    def has_form(self) -> bool:
        return bool(self.form)

    def execute_url(self) -> str:
        return reverse("core:zaak-task", args=[self.id])

    def get_variable(self, name: str) -> Any:
        return get_task_variable(self.id, name)
