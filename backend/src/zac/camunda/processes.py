from typing import Dict, List

from django_camunda.camunda_models import ProcessDefinition
from django_camunda.client import Camunda, get_client
from zgw_consumers.api_models.base import factory
from zgw_consumers.concurrent import parallel

from zac.camunda.data import ProcessInstance
from zac.camunda.messages import get_messages
from zac.core.camunda import get_process_tasks


def get_process_definitions(definition_ids: list) -> List[ProcessDefinition]:
    client = get_client()
    response = client.get(
        "process-definition", {"processDefinitionIdIn": ",".join(definition_ids)}
    )
    return factory(ProcessDefinition, response)


def add_subprocesses(
    process_instance: ProcessInstance,
    process_instances: Dict[str, ProcessInstance],
    client: Camunda,
    historic: bool = False,
):
    if process_instance.sub_processes:
        return

    if historic:
        url = "history/process-instance"
        query_params = {"superProcessInstanceId": process_instance.id}
    else:
        url = "process-instance"
        query_params = {"superProcessInstance": process_instance.id}

    response = client.get(url, query_params)

    # todo restrict for other zaakUrls
    for data in response:
        sub_process_instance = process_instances.get(
            data["id"], factory(ProcessInstance, {**data, "historical": historic})
        )

        sub_process_instance.parent_process = process_instance
        process_instance.sub_processes.append(sub_process_instance)
        if (
            sub_process_instance.id not in process_instances
            or sub_process_instance != process_instances[sub_process_instance.id]
        ):
            process_instances[sub_process_instance.id] = sub_process_instance
            add_subprocesses(
                sub_process_instance, process_instances, client, historic=historic
            )


def get_process_instances(
    zaak_url: str, historic: bool = False
) -> List[ProcessInstance]:
    client = get_client()

    #  get (historical) process-instances for particular zaak
    if historic:
        url = "history/process-instance"
    else:
        url = "process-instance"

    response = client.get(url, {"variables": f"zaakUrl_eq_{zaak_url}"})

    process_instances = {
        data["id"]: factory(ProcessInstance, {**data, "historical": historic})
        for data in response
    }
    # fill in all subprocesses into the dict
    pids = [
        process_instance for id, process_instance in process_instances.copy().items()
    ]

    def _add_subprocesses(pid: ProcessInstance):
        nonlocal process_instances, client, historic
        add_subprocesses(pid, process_instances, client, historic=historic)

    with parallel() as executor:
        list(executor.map(_add_subprocesses, pids))

    return process_instances


def get_top_level_process_instances(zaak_url: str) -> List[ProcessInstance]:
    process_instances = get_process_instances(zaak_url)
    # add definitions add user tasks
    definition_ids = [p.definition_id for p in process_instances.values()]
    definitions = {
        definition.id: definition
        for definition in get_process_definitions(definition_ids)
    }
    process_instances_without_task = []
    for id, process_instance in process_instances.items():
        process_instance.definition = definitions[process_instance.definition_id]
        if not process_instance.tasks:
            process_instances_without_task.append(process_instance)

    with parallel() as executor:
        results = executor.map(get_process_tasks, process_instances_without_task)

    tasks = {str(_tasks[0].process_instance_id): _tasks for _tasks in results if _tasks}
    for id, process_instance in process_instances.items():
        if not process_instance.tasks:
            process_instance.tasks = tasks.get(str(process_instance.id), [])

    # get messages only for top level processes
    top_level_processes = [
        p for p in process_instances.values() if not p.parent_process
    ]
    top_definition_ids = {p.definition_id for p in top_level_processes}
    def_messages: Dict[str, List[str]] = {}

    def _get_messages(definition_id: str):
        nonlocal def_messages
        def_messages[definition_id] = get_messages(definition_id)

    with parallel() as executor:
        list(executor.map(_get_messages, top_definition_ids))

    for process in top_level_processes:
        process.messages = def_messages[process.definition_id]

    return top_level_processes
