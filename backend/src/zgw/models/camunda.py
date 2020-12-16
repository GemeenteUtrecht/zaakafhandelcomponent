from dataclasses import dataclass

from .base import BaseModel


@dataclass
class Task(BaseModel):
    id: str
    name: str
    assignee: str
    created: str
    due: str
    follow_up: str
    delegation_state: str
    description: str
    execution_id: str
    owner: str
    parent_task_id: str
    priority: int
    process_definition_id: str
    process_instance_id: str
    task_definition_key: str
    case_execution_id: str
    case_instance_id: str
    case_definition_id: str
    suspended: bool
    form_key: str
    tenant_id: str
