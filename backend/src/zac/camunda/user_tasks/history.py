from typing import Dict, List, Optional

from django.conf import settings

from django_camunda.client import Camunda, get_client
from django_camunda.types import CamundaId
from django_camunda.utils import deserialize_variable
from zgw_consumers.api_models.base import factory
from zgw_consumers.concurrent import parallel

from zac.camunda.api.data import HistoricUserTask
from zac.camunda.data import Task
from zac.camunda.dynamic_forms.context import get_field_definition
from zac.camunda.forms import extract_task_form_fields, extract_task_form_key


def get_task_history(json: Dict, client: Optional[Camunda] = None) -> Dict[str, Dict]:
    if not client:
        client = get_client()

    results = client.post("history/task", json=json)
    return results


def get_completed_user_tasks_for_zaak(
    zaak_url: str, client: Optional[Camunda] = None
) -> Dict[CamundaId, Task]:
    """
    The camunda rest api exposes the historic (i.e., completed) user tasks
    of completed and ongoing process instances.

    We use the historic user tasks data to show who submitted what at
    which date.
    """
    if not client:
        client = get_client()

    tasks = get_task_history(
        client=client,
        json={
            "processVariables": [
                {"name": "zaakUrl", "operator": "eq", "value": zaak_url}
            ],
            "finished": True,
        },
    )

    # Abuse for factory purposes
    tasks = [
        factory(
            Task,
            {
                **task,
                "created": task["start_time"],
                "delegation_state": None,
                "suspended": False,
                "form_key": None,
            },
        )
        for task in tasks
    ]
    return {task.id: task for task in tasks}


def get_historic_activity_details(
    activity_instance_id: str, client: Optional[Camunda] = None
) -> List[dict]:
    if not client:
        client = get_client()

    historic_activity_details = client.get(
        "history/detail",
        {"activityInstanceId": activity_instance_id, "deserializeValues": False},
    )
    return historic_activity_details


def get_historic_activity_variables_from_task(
    task: Task, client: Optional[Camunda] = None
) -> List[dict]:
    """
    The camunda rest api exposes the historic details of a process.

    We use the historic details to match variable instances
    to a particular activity instance. The activity instance
    is then related to the user task that has the same activity
    instance.
    """
    if not client:
        client = get_client()

    historic_activity_details = get_historic_activity_details(
        task.activity_instance_id, client=client
    )
    # If variable_name is none, the information for now is deemed irrelevant.
    historic_activity_details = [
        detail
        for detail in historic_activity_details
        if detail.get("variable_name")
        and detail.get("variable_name") not in settings.FILTERED_CAMUNDA_VARIABLES
    ]

    for detail in historic_activity_details:
        # func deserialize_variable requires the `type` key - not `variable_type`.
        detail["type"] = detail["variable_type"]
        detail["value"] = deserialize_variable(detail)

    return sorted(historic_activity_details, key=lambda obj: obj["variable_name"])


def get_historic_form_labels_from_task(task: Task) -> Dict[str, str]:
    """
    From the BPMN definition we can retrieve form field data such as labels.

    We use the labels to replicate the form the user was presented at a
    particular point in a process.
    """

    formfields = extract_task_form_fields(task) or []
    form_fields = [get_field_definition(field) for field in formfields]

    # Aggregate variable values
    form_variables = {}
    for form_field in form_fields:
        form_variables[form_field["name"]] = form_field["label"]

    return form_variables


def get_camunda_history_for_zaak(
    zaak_url: str,
) -> List[HistoricUserTask]:
    """
    The completed camunda user tasks are fetched here and returned in reverse order based
    on creation date.

    First the completed user tasks for a zaak_url are fetched from the camunda rest api
    based on the (historical) process instances that have the zaak_url as a process variable.

    Based on the task activity instance, the historical variable instances are then fetched.
    Finally, the variable instance is enriched with form labels in case the user task has a
    camunda user form. The form key of the user task is not returned from the camunda rest
    api and so it needs to be fetched separately from the BPMN file.
    """
    tasks = get_completed_user_tasks_for_zaak(zaak_url)

    def _extract_task_form_key(task: Task):
        nonlocal tasks
        tasks[task.id].form_key = extract_task_form_key(task)

    # Get task form_keys
    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        list(
            executor.map(
                _extract_task_form_key,
                [task for task in tasks.values()],
            )
        )

    # Declare zaak_history for non-local use in _get_historic_activity_variables_from_task
    user_task_history = {}
    client = get_client()

    # Get all variables that are set in activity instance of task
    def _get_historic_activity_variables_from_task(task: Task):
        nonlocal client, user_task_history
        history = get_historic_activity_variables_from_task(task, client=client)
        user_task_history[task.id] = {
            "task": task,
            "history": history,
        }

    tasks = tasks.values()
    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        list(executor.map(_get_historic_activity_variables_from_task, tasks))

    # Add camunda form labels to zaak_history if task has a camunda form
    def _add_camunda_form_labels_to_user_task_history(task: Task):
        nonlocal user_task_history
        form_labels = get_historic_form_labels_from_task(task)
        for var in user_task_history[task.id]["history"]:
            if form_label := form_labels.get(var["variable_name"]):
                var["label"] = form_label

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        list(executor.map(_add_camunda_form_labels_to_user_task_history, tasks))

    return factory(HistoricUserTask, [h for h in user_task_history.values()])
