from typing import List

from django_camunda.client import get_client
from zgw_consumers.api_models.base import factory

from .data import ProcessInstance


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

    #  display them prettily
    top_level_processes = list(
        filter(lambda x: not x.parent_process, process_instances.values())
    )
    return top_level_processes
