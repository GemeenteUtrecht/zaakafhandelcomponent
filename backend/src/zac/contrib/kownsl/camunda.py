from dataclasses import dataclass
from typing import List

from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.camunda.data import Task
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.kownsl.constants import KownslTypes
from zac.core.camunda import get_process_zaak_url, get_task
from zac.core.services import fetch_zaaktype, get_documenten, get_zaak


@dataclass
class AdviceApprovalContext(Context):
    review_type: str
    title: str
    zaak: Zaak
    documents: List[Document]


class ZaakInformatieTaskSerializer(APIModelSerializer):
    # TODO: Write tests.
    class Meta:
        model = Zaak
        fields = (
            "omschrijving",
            "toelichting",
        )


class DocumentUserTaskSerializer(APIModelSerializer):
    # TODO: Write tests.
    read_url = serializers.SerializerMethodField(
        label=_("ZAC document read URL"),
        help_text=_(
            "A URL that on POST request returns a magicUrl to the document on a webdav server."
        ),
    )

    class Meta:
        model = Document
        fields = (
            "beschrijving",
            "bestandsnaam",
            "read_url",
            "url",
        )

    def get_read_url(self, obj) -> str:
        path = reverse(
            "dowc:request-doc",
            kwargs={
                "bronorganisatie": obj.bronorganisatie,
                "identificatie": obj.identificatie,
                "purpose": DocFileTypes.read,
            },
        )
        return self.context["request"].build_absolute_uri(path)


class AdviceApprovalContextSerializer(APIModelSerializer):
    # TODO: Write tests.
    documents = DocumentUserTaskSerializer(many=True)
    zaak_informatie = ZaakInformatieTaskSerializer()

    class Meta:
        model = AdviceApprovalContext
        fields = ("documents", "title", "zaak_informatie")


@usertask_context_serializer
class AdviceContextSerializer(AdviceApprovalContextSerializer):
    review_type = serializers.CharField(default="advice")

    class Meta(AdviceApprovalContextSerializer.Meta):
        fields = AdviceApprovalContextSerializer.Meta.fields + ("review_type",)


@usertask_context_serializer
class ApprovalContextSerializer(AdviceApprovalContextSerializer):
    review_type = serializers.CharField(default="approval")

    class Meta(AdviceApprovalContextSerializer.Meta):
        fields = AdviceApprovalContextSerializer.Meta.fields + ("review_type",)


@register(
    "zac:configureApprovalRequest", ApprovalContextSerializer, ApprovalContextSerializer
)
@register(
    "zac:configureAdviceRequest", AdviceContextSerializer, AdviceContextSerializer
)
def get_context(task: Task) -> AdviceApprovalContext:
    # TODO: Write tests.
    process_instance = get_process_instance(task.process_instance_id)
    zaak_url = get_process_zaak_url(process_instance)
    zaak = get_zaak(zaak_url=zaak_url)
    zaaktype = fetch_zaaktype(zaak.zaaktype)
    documents = get_documenten(zaak)
    return AdviceApprovalContext(
        title=f"{zaaktype.omschrijving} - {zaaktype.versiedatum}",
        zaak=zaak,
        documents=documents,
    )
