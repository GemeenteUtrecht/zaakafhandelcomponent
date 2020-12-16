import uuid

from django.utils import timezone


def get_camunda_task_mock(**kwargs):
    defaults = {
        "id": str(uuid.uuid4()),
        "name": "dummy",
        "assignee": None,
        "created": timezone.now().isoformat(),
        "due": None,
        "follow_up": None,
        "delegation_state": None,
        "description": None,
        "execution_id": "some-execution",
        "owner": None,
        "parent_task_id": None,
        "priority": 0,
        "process_definition_id": "some-process-definition",
        "process_instance_id": str(uuid.uuid4()),
        "task_definition_key": "",
        "case_execution_id": None,
        "case_instance_id": None,
        "case_definition_id": None,
        "suspended": False,
        "form_key": None,
        "tenant_id": None,
    }
    return {**defaults, **kwargs}
