from typing import Dict, List

from django_camunda.camunda_models import ProcessDefinition
from django_camunda.client import Camunda, get_client
from zgw_consumers.api_models.base import factory

from zac.core.camunda import get_process_tasks

from .data import ProcessInstance
from .messages import get_messages


def get_process_definitions(definition_ids: list) -> List[ProcessDefinition]:
    client = get_client()
    response = client.get(
        f"process-definition", {"processDefinitionIdIn": ",".join(definition_ids)}
    )
    return factory(ProcessDefinition, response)


def add_subprocesses(
    process_instance: ProcessInstance,
    process_instances: Dict[str, ProcessInstance],
    client: Camunda,
):
    if process_instance.sub_processes:
        return

    response = client.get(
        "process-instance", {"superProcessInstance": process_instance.id}
    )
    # todo restrict for other zaakUrls
    for data in response:
        sub_process_instance = process_instances.get(
            data["id"], factory(ProcessInstance, data)
        )

        sub_process_instance.parent_process = process_instance
        process_instance.sub_processes.append(sub_process_instance)
        process_instances[sub_process_instance.id] = sub_process_instance

        add_subprocesses(sub_process_instance, process_instances, client)


def get_process_instances(zaak_url: str) -> List[ProcessInstance]:
    client = get_client()

    #  get process-instances for particular zaak
    response = client.get("process-instance", {"variables": f"zaakUrl_eq_{zaak_url}"})
    process_instances = {
        data["id"]: factory(ProcessInstance, data) for data in response
    }

    # fill in all subpocesses into the dict
    for id, process_instance in process_instances.copy().items():
        add_subprocesses(process_instance, process_instances, client)

    # add definitions add user tasks
    definition_ids = [p.definition_id for p in process_instances.values()]
    definitions = {
        definition.id: definition
        for definition in get_process_definitions(definition_ids)
    }
    for id, process_instance in process_instances.items():
        process_instance.definition = definitions[process_instance.definition_id]
        if not process_instance.tasks:
            process_instance.tasks = get_process_tasks(process_instance)

    # get messages only for top level processes
    top_level_processes = [
        p for p in process_instances.values() if not p.parent_process
    ]
    top_definition_ids = {p.definition_id for p in top_level_processes}
    def_messages = {
        definition_id: get_messages(definition_id)
        for definition_id in top_definition_ids
    }
    for process in top_level_processes:
        process.messages = def_messages[process.definition_id]

    return top_level_processes
