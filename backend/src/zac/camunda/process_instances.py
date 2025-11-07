from typing import Any, Dict, List, Optional, Union

from django.conf import settings

import requests
from django_camunda.camunda_models import ProcessDefinition, factory
from django_camunda.client import Camunda, get_client
from django_camunda.types import CamundaId
from django_camunda.utils import serialize_variable
from zgw_consumers.api_models.base import factory
from zgw_consumers.concurrent import parallel

from zac.camunda.data import HistoricProcessInstance, ProcessInstance
from zac.camunda.messages import get_messages
from zac.core.camunda.utils import get_process_tasks
from zac.core.utils import A_DAY
from zac.utils.decorators import cache


@cache("process-instance:{instance_id}", timeout=2)
def get_process_instance(
    instance_id: CamundaId,
) -> Optional[Union[ProcessInstance, HistoricProcessInstance]]:
    client = get_client()
    try:
        data = client.get(f"process-instance/{instance_id}")
    except requests.HTTPError as exc:
        if exc.response.status_code != 404:
            raise

        # check the history
        try:
            data = client.get(f"history/process-instance/{instance_id}")
        except requests.HTTPError as history_exc:
            if history_exc.response.status_code == 404:
                return None
            raise

        data.update(
            {
                "definition_id": data["process_definition_id"],
                "historical": True,
            }
        )
    return factory(
        ProcessInstance if not data.get("historical") else HistoricProcessInstance, data
    )


def delete_process_instance(instance_id: CamundaId, query_params: Dict = dict):
    client = get_client()
    query_params = {
        "skipIoMappings": "true",
    }
    client.delete(f"process-instance/{instance_id}", params=query_params)


@cache("get_process_definitions:{cache_key}", timeout=A_DAY)
def get_process_definitions(
    definition_ids: list, cache_key: str
) -> List[ProcessDefinition]:
    if not definition_ids:
        return []

    client = get_client()
    response = client.get(
        "process-definition", {"processDefinitionIdIn": ",".join(definition_ids)}
    )
    return factory(ProcessDefinition, response)


def add_subprocesses(
    process_instance: Union[ProcessInstance, HistoricProcessInstance],
    process_instances: Dict[str, Union[ProcessInstance, HistoricProcessInstance]],
    client: Camunda,
    historic: bool = False,
    zaak_url: str = "",
):
    if process_instance.sub_processes:
        return

    if historic:
        url = "history/process-instance"
        query_params = {"superProcessInstanceId": process_instance.id}
    else:
        url = "process-instance"
        query_params = {"superProcessInstance": process_instance.id}

    # If zaak_url is given ONLY include process instances with that zaak url
    if zaak_url:
        query_params["variables"] = f"zaakUrl_eq_{zaak_url}"

    response = client.get(url, query_params)

    # todo restrict for other zaakUrls
    for data in response:
        sub_process_instance = process_instances.get(
            data["id"],
            factory(
                ProcessInstance if not historic else HistoricProcessInstance,
                {**data, "historical": historic},
            ),
        )

        sub_process_instance.parent_process = process_instance
        process_instance.sub_processes.append(sub_process_instance)
        if (
            sub_process_instance.id not in process_instances
            or sub_process_instance != process_instances[sub_process_instance.id]
        ):
            process_instances[sub_process_instance.id] = sub_process_instance
            add_subprocesses(
                sub_process_instance,
                process_instances,
                client,
                historic=historic,
                zaak_url=zaak_url,
            )


def get_process_instances(
    zaak_url: str,
    historic: bool = False,
    include_bijdragezaak: bool = False,
    exclude_zaak_creation: bool = True,
    nest: bool = False,
    process_definition_key: str = "",
) -> Dict[CamundaId, Union[HistoricProcessInstance, ProcessInstance]]:
    client = get_client()

    #  get (historical) process-instances for particular zaak
    if historic:
        url = "history/process-instance"
    else:
        url = "process-instance"

    query_params = {"variables": f"zaakUrl_eq_{zaak_url}"}
    if exclude_zaak_creation:
        query_params["processDefinitionKeyNotIn"] = (
            settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY
        )

    if process_definition_key:
        query_params["processDefinitionKey"] = process_definition_key

    response = client.get(url, query_params)

    process_instances = {
        data["id"]: factory(
            ProcessInstance if not historic else HistoricProcessInstance,
            {**data, "historical": historic},
        )
        for data in response
    }

    if nest:
        # fill in all subprocesses into the dict
        pis = [process_instance for id, process_instance in process_instances.items()]

        def _add_subprocesses(pi: Union[ProcessInstance, HistoricProcessInstance]):
            nonlocal process_instances, client, historic, include_bijdragezaak, zaak_url
            add_subprocesses(
                pi,
                process_instances,
                client,
                historic=historic,
                zaak_url="" if include_bijdragezaak else zaak_url,
            )

        with parallel(max_workers=settings.MAX_WORKERS) as executor:
            list(executor.map(_add_subprocesses, pis))

    definition_ids = sorted(
        list(
            set(
                [p.definition_id for p in process_instances.values() if p.definition_id]
            )
        )
    )
    cache_key = hash("".join(definition_ids))
    definitions = {
        definition.id: definition
        for definition in get_process_definitions(definition_ids, cache_key)
    }
    for id, process_instance in process_instances.items():
        process_instance.definition = definitions.get(
            process_instance.definition_id, None
        )
    return process_instances


def get_top_level_process_instances(
    zaak_url: str,
    include_bijdragezaak: bool = False,
    exclude_zaak_creation: bool = True,
) -> List[ProcessInstance]:
    process_instances = get_process_instances(
        zaak_url,
        include_bijdragezaak=include_bijdragezaak,
        exclude_zaak_creation=exclude_zaak_creation,
        nest=True,
    )

    # add user tasks
    process_instances_without_task = []
    for id, process_instance in process_instances.items():
        if not process_instance.tasks:
            process_instances_without_task.append(process_instance)

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        results = executor.map(get_process_tasks, process_instances_without_task)

    tasks = {str(_tasks[0].process_instance_id): _tasks for _tasks in results if _tasks}
    for id, process_instance in process_instances.items():
        if not process_instance.tasks:
            process_instance.tasks = tasks.get(str(process_instance.id), [])

    # get messages only for top level processes
    top_level_processes = [
        p for p in process_instances.values() if not p.parent_process
    ]
    top_definition_ids = {
        p.definition_id for p in top_level_processes if p.definition_id
    }
    def_messages: Dict[str, List[str]] = {}

    def _get_messages(definition_id: str):
        nonlocal def_messages
        def_messages[definition_id] = get_messages(definition_id)

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        list(executor.map(_get_messages, top_definition_ids))

    for process in top_level_processes:
        process.messages = def_messages.get(process.definition_id, None)

    return top_level_processes


def update_process_instance_variable(
    pid: CamundaId, variable_name: str, variable_value: Any
):
    """
    Serializes and updates a variable in a process instance
    in Camunda.

    """
    camunda_client = get_client()
    camunda_client.put(
        f"process-instance/{pid}/variables/{variable_name}",
        json=serialize_variable(variable_value),
    )
