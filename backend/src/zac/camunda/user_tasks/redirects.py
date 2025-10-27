"""
User tasks of the type zac:doRedirect.
"""

from dataclasses import dataclass

from furl import furl
from zgw_consumers.drf.serializers import APIModelSerializer

from ..data import Task
from . import Context, register, usertask_context_serializer


@dataclass
class RedirectContext(Context):
    redirect_to: str
    open_in_new_window: bool
    end_task: bool


@usertask_context_serializer
class RedirectContextSerializer(APIModelSerializer):
    class Meta:
        model = RedirectContext
        fields = ("redirect_to", "open_in_new_window", "end_task")


@register("zac:doRedirect", RedirectContextSerializer)
def get_redirect_task_context(task: Task) -> RedirectContext:
    redirect_url = task.get_variable("redirectTo")
    query_params = task.get_variable("queryParams", default=None)
    if query_params:
        redirect_url = furl(redirect_url).add(query_params).url
    new_window = task.get_variable("openInNewWindow", default=False)
    end_task = task.get_variable("endTask", default=True)
    return RedirectContext(
        redirect_to=redirect_url, open_in_new_window=new_window, end_task=end_task
    )
