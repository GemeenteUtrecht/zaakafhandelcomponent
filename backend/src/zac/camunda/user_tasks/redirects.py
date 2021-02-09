"""
User tasks of the type zac:doRedirect.
"""
from dataclasses import dataclass

from django_camunda.api import get_task_variable
from zgw_consumers.drf.serializers import APIModelSerializer

from ..data import Task
from . import Context, register, usertask_context_serializer


@dataclass
class RedirectContext(Context):
    redirect_to: str
    open_in_new_window: bool


@usertask_context_serializer
class RedirectContextSerializer(APIModelSerializer):
    class Meta:
        model = RedirectContext
        fields = ("redirect_to", "open_in_new_window")


@register("zac:doRedirect", RedirectContextSerializer, RedirectContextSerializer)
def get_redirect_task_context(task: Task) -> RedirectContext:
    redirect_url = get_task_variable(task.id, "redirectTo")
    new_window = get_task_variable(task.id, "openInNewWindow", False)
    return RedirectContext(
        redirect_to=redirect_url,
        open_in_new_window=new_window,
    )
