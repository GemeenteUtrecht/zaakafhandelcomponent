from dataclasses import dataclass
from typing import List

from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, register, usertask_context_serializer


@dataclass
class AdviceApprovalContext(Context):
    review_type: str
    title: str
    zaak: Zaak
    documents: List[Document]


@usertask_context_serializer
class AdviceApprovalContextSerializer(APIModelSerializer):
    class Meta:
        model = AdviceApprovalContext
        fields = ("review_type", "title")


@register("zac:configureApprovalRequest", AdviceApprovalContextSerializer)
@register("zac:configureAdviceRequest", AdviceApprovalContextSerializer)
def get_context(task: Task) -> AdviceApprovalContext:
    return AdviceApprovalContext(
        review_type="approval",
        title="Test Polymorphic serializers",
        zaak=None,
        documents=[],
    )
