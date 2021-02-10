from dataclasses import dataclass

from zgw_consumers.drf.serializers import APIModelSerializer

from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, register, usertask_context_serializer


@dataclass
class ValidSignContext(Context):
    pass


@usertask_context_serializer
class ValidSignSerializer(APIModelSerializer):
    class Meta:
        model = ValidSignContext
        fields = ()


@register("zac:validSign:configurePackage", ValidSignSerializer)
def get_context(task: Task) -> ValidSignContext:
    return ValidSignContext()
