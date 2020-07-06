from django_camunda.client import Camunda

from zgw.models.camunda import Task


def get_tasks(zaken):
    client = Camunda()
    # FIXME filter on particular zaak when relationship of zaak and tasks appears
    _tasks_raw = client.request(f"task")
    return [Task.from_raw(_task) for _task in _tasks_raw]
