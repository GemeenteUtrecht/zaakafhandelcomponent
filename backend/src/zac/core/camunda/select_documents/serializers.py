from dataclasses import dataclass
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.drf.serializers import APIModelSerializer
from zgw_consumers.models import Service
from zgw_consumers.service import get_paginated_results

from zac.api.context import get_zaak_context
from zac.camunda.user_tasks import Context, usertask_context_serializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.fields import DowcUrlFieldReadOnly
from zac.core.services import get_documenten


class DocumentSerializer(APIModelSerializer):
    document_type = serializers.CharField(source="informatieobjecttype.omschrijving")
    read_url = DowcUrlFieldReadOnly(purpose=DocFileTypes.read)

    class Meta:
        model = Document
        fields = (
            "beschrijving",
            "bestandsnaam",
            "bestandsomvang",
            "document_type",
            "read_url",
            "url",
            "versie",
        )


@dataclass
class DocumentSelectContext(Context):
    documents: List[Document]


@usertask_context_serializer
class DocumentSelectContextSerializer(APIModelSerializer):
    documents = DocumentSerializer(many=True)

    class Meta:
        model = DocumentSelectContext
        fields = ("documents",)


#
# Write serializer
#


class SelectedDocumentSerializer(serializers.Serializer):
    document = serializers.ChoiceField(
        label=_("Selected document"),
        help_text=_("The URL of the selected document from the relevant case."),
        choices=(),
    )

    document_type = serializers.ChoiceField(
        label=_("Selected document type"),
        help_text=_("The URL of the selected document type."),
        choices=(),
    )


class DocumentSelectTaskSerializer(serializers.Serializer):
    """
    Serializes the selected documents for the task.

    Requires ``task`` to be in serializer ``context``.
    """

    selected_documents = SelectedDocumentSerializer(many=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set valid choices for selecting documents
        zaak = self.get_zaak_from_context()
        documents, _gone = get_documenten(zaak)
        self.fields["selected_documents"].fields["document"].choices = [
            doc.url for doc in documents
        ]

        # Set valid choices for selecting document types
        ztcs = Service.objects.filter(api_type=APITypes.ztc)
        eiots = []
        for ztc in ztcs:
            client = ztc.build_client()
            results = get_paginated_results(client, "informatieobjecttype")
            eiots += [iot["url"] for iot in results]

        self.fields["selected_documents"].fields["document_type"].choices = list(
            set(eiots)
        )

    def get_zaak_from_context(self):
        zaak_context = get_zaak_context(self.context["task"])
        return zaak_context.zaak

    def get_process_variables(self) -> Dict:
        """
        #TODO: ?
        """
        return {}

    def on_task_submission(self) -> None:
        """
        #TODO: ?
        """
        pass
