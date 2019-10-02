from django_camunda.client import Camunda
from zgw.models.camunda import ProcessInstance


def get_process_instances():
    client = Camunda()
    _process_instances_raw = client.request(f"process-instance")
    return [ProcessInstance.from_raw(instance) for instance in _process_instances_raw]

