from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from django.contrib.auth.models import Group

from django_camunda.api import get_process_instance_variable, get_task_variable
from django_camunda.camunda_models import Model, Task as _Task
from django_camunda.client import get_client
from django_camunda.types import CamundaId

from zac.accounts.models import User

from .constants import AssigneeTypeChoices
from .history import get_historical_variable


@dataclass
class BaseProcessInstance(Model, ABC):
    id: CamundaId
    business_key: str = ""
    case_instance_id: str = ""
    suspended: bool = False
    tenant_id: str = ""

    definition: Optional[str] = None
    sub_processes: list = field(default_factory=list)
    parent_process: str = None
    messages: list = field(default_factory=list)
    tasks: list = field(default_factory=list)

    @abstractmethod
    def get_variable(self, name: str) -> Any:
        raise NotImplementedError("Please implement get_variable on subclasses.")

    def title(self) -> str:
        return self.definition.name or self.definition.key

    @abstractmethod
    def get_url(self) -> str:
        raise NotImplementedError("Please implement get_url on subclasses.")


@dataclass
class ProcessInstance(BaseProcessInstance):
    definition_id: str = ""
    historical: bool = False

    def get_variable(self, name: str) -> Any:
        return get_process_instance_variable(self.id, name)

    def get_url(self) -> str:
        client = get_client()
        return f"{client.root_url}process-instance/{self.id}"


@dataclass
class HistoricProcessInstance(BaseProcessInstance):
    process_definition_id: str = ""
    historical: bool = True

    @property
    def definition_id(self) -> str:
        return self.process_definition_id

    def get_variable(self, name: str) -> Any:
        return get_historical_variable(self.id, name)

    def get_url(self) -> str:
        client = get_client()
        return f"{client.root_url}history/process-instance/{self.id}"


@dataclass
class Task(_Task):
    historical: bool = False
    end_time: Optional[datetime] = None
    activity_instance_id: Optional[CamundaId] = None
    form = None

    def has_form(self) -> bool:
        return bool(self.form)

    def get_variable(self, name: str, default: Optional[Any] = None) -> Any:
        return get_task_variable(self.id, name, default=default)

    def assignee_type(self) -> str:
        if self.assignee:
            if isinstance(self.assignee, User):
                return AssigneeTypeChoices.user
            elif isinstance(self.assignee, Group):
                return AssigneeTypeChoices.group
        return ""


@dataclass
class BPMN:
    id: str
    bpmn20_xml: str
