from dataclasses import dataclass, field

from django_camunda.camunda_models import Task as _Task
from django_camunda.types import CamundaId
from zgw_consumers.api_models.base import Model


@dataclass
class ProcessInstance(Model):
    id: CamundaId
    definition_id: str

    sub_processes: list = field(default_factory=list)
    parent_process: str = None
    zaak_url: str = None
    messages: list = field(default_factory=list)
    tasks: list = field(default_factory=list)


@dataclass
class Task(_Task):
    def has_form(self) -> bool:
        return bool(self.form)
