from typing import Dict, List, Optional

from django_camunda.client import Camunda, get_client
from django_camunda.types import CamundaId
from django_camunda.utils import deserialize_variable
from zgw_consumers.api_models.base import factory
from zgw_consumers.concurrent import parallel

from zac.camunda.data import Task
from zac.camunda.dynamic_forms.context import get_field_definition
from zac.camunda.forms import extract_task_form_fields, extract_task_form_key
from zac.core.services import A_DAY
from zac.utils.decorators import cache

from ..api.data import HistoricActivityInstanceDetail, HistoricUserTask
from ..data import Task
from ..processes import get_process_instances


@cache("historical_tasks:{pid}", timeout=A_DAY)
def get_task_history_for_process_instance(
    pid: CamundaId, client: Camunda
) -> Dict[str, Dict]:
    results = client.get("history/task", {"processInstanceId": pid, "finished": "true"})
    tasks = {}
    for task in results:
        tasks[task["id"]] = task
    return tasks


def get_completed_user_tasks_for_zaak(
    zaak_url: str, client: Optional[Camunda] = None
) -> Dict[CamundaId, Task]:
    """
    The camunda rest api exposes the historic (i.e., finished) user tasks
    of completed and ongoing process instances.

    We use the historic user tasks data to show who submitted what at
    which date.
    """
    if not client:
        client = get_client()

    historic_process_instances = get_process_instances(zaak_url, historic=True)
    active_process_instances = get_process_instances(zaak_url)
    all_process_instances = {**historic_process_instances, **active_process_instances}

    tasks = {}

    def _get_historic_tasks(pid: CamundaId):
        nonlocal client, tasks
        tasks.update(**get_task_history_for_process_instance(pid, client))

    with parallel() as executor:
        list(executor.map(_get_historic_tasks, all_process_instances.keys()))

    tasks = [
        factory(
            Task,
            {
                **task,
                "created": task["start_time"],
                "delegation_state": None,
                "suspended": True,
                "form_key": None,
            },
        )
        for task in tasks.values()
    ]

    return {task.id: task for task in tasks}


@cache("historical_activity_detail:{activity_instance_id}", timeout=A_DAY)
def get_historic_activity_details(activity_instance_id: str) -> List[dict]:
    client = get_client()
    historic_activity_details = client.get(
        "history/detail",
        {"activityInstanceId": activity_instance_id, "deserializeValues": False},
    )
    return historic_activity_details


def get_historic_activity_variables_from_task(
    task: Task, client: Optional[Camunda] = None
) -> List[HistoricActivityInstanceDetail]:
    """
    The camunda rest api exposes the historic details of a process.

    We use the historic details to match variable instances
    to a particular activity instance. The activity instance
    is then related to the user task that has the same activity
    instance.
    """
    if not client:
        client = get_client()

    historic_activity_details = get_historic_activity_details(task.activity_instance_id)
    for detail in historic_activity_details:
        detail["type"] = detail["variable_type"]
        detail["value"] = deserialize_variable(detail)

    return factory(HistoricActivityInstanceDetail, historic_activity_details)


def get_historic_form_labels_from_task(
    task: Task, client: Optional[Camunda] = None
) -> Dict[str, str]:
    """
    From the BPMN definition we can retrieve form field data such as labels.

    We use the labels to replicate the form the user was presented in at a
    particular point in a process.
    """
    if not client:
        client = get_client()

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
    The finished camunda user tasks are fetched here and returned in reverse order based on creation date.

    First the completed user tasks for a zaak_url are fetched. They are fetched from the camunda rest api
    based on the (historical) process instances that have the zaak_url as a process variable.

    The form key of the user task is not returned from the camunda rest api
    and so it needs to be fetched separately based on the BPMN.

    Based on the task activity instance, the historical variable instances are fetched.
    The variable instance is then enriched in case the user task has a camunda user form.
    """
    client = get_client()
    tasks = get_completed_user_tasks_for_zaak(zaak_url, client=client)

    def _extract_task_form_key(task: Task):
        nonlocal tasks
        tasks[task.id].form_key = extract_task_form_key(task)

    # Get task form_keys
    with parallel() as executor:
        list(
            executor.map(
                _extract_task_form_key,
                [task for task in tasks.values()],
            )
        )

    # Declare zaak_history for non-local use in _get_historic_activity_variables_from_task
    user_task_history = {}

    # Get all variables that are set in activity instance of task
    def _get_historic_activity_variables_from_task(task: Task):
        nonlocal client, user_task_history
        history = get_historic_activity_variables_from_task(task, client)
        user_task_history[task.id] = {
            "task": task,
            "history": history,
        }

    tasks = tasks.values()
    with parallel() as executor:
        list(executor.map(_get_historic_activity_variables_from_task, tasks))

    # Add camunda form labels to zaak_history if task has a camunda form
    def _add_camunda_form_labels_to_user_task_history(task: Task):
        nonlocal client, user_task_history
        if task.form_key:
            return

        form_labels = get_historic_form_labels_from_task(task, client)

        for var in user_task_history[task.id]["history"]:
            if form_label := form_labels.get(var.variable_name):
                var.label = form_label

    with parallel() as executor:
        list(executor.map(_add_camunda_form_labels_to_user_task_history, tasks))

    # Latest task shows first
    return sorted(
        factory(HistoricUserTask, [h for h in user_task_history.values()]),
        key=lambda h: h.task.created,
        reverse=True,
    )


zaak_url = "https://open-zaak.cg-intern.ont.utrecht.nl/zaken/api/v1/zaken/b724f70f-e6b8-4514-b7c5-0017a3f635ca"
