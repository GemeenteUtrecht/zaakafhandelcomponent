from typing import List

from django.urls import reverse

from django_camunda.client import get_client
from zgw_consumers.api_models.base import factory

from zac.core.camunda import get_process_tasks
from zac.core.services import get_zaak

from .data import ProcessInstance
from .messages import get_messages


def add_subprocesses(process_instance, process_instances, client):
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

    process_instances = {}
    for data in response:
        process_instance = factory(ProcessInstance, data)
        process_instance.zaak_url = zaak_url
        process_instances[data["id"]] = process_instance

    # fill in all subpocesses into the dict
    #  todo concurrency?
    for id, process_instance in process_instances.copy().items():
        add_subprocesses(process_instance, process_instances, client)

    # add user tasks
    for id, process_instance in process_instances.items():
        if not process_instance.tasks:
            process_instance.tasks = get_process_tasks(process_instance)

    #  display them prettily
    top_level_processes = [
        p for p in process_instances.values() if not p.parent_process
    ]
    #  add messages for top level processes
    definition_ids = {p.definition_id for p in top_level_processes}
    def_messages = {
        definition_id: get_messages(definition_id) for definition_id in definition_ids
    }
    for process in top_level_processes:
        process.messages = def_messages[process.definition_id]

    return top_level_processes
