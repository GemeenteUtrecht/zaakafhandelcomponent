from dataclasses import dataclass
from typing import Dict, List

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.context import get_zaak_context
from zac.camunda.user_tasks import Context, usertask_context_serializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url
from zac.core.api.fields import SelectDocumentsField


class DocumentSerializer(APIModelSerializer):
    read_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "beschrijving",
            "bestandsnaam",
            "bestandsomvang",
            "url",
            "read_url",
            "versie",
        )

    def get_read_url(self, obj) -> str:
        """
        Create the document read url to facilitate opening the document
        in a MS WebDAV client.
        """
        return get_dowc_url(obj, purpose=DocFileTypes.read)


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


class DocumentSelectTaskSerializer(serializers.Serializer):
    """
    Serializes the selected documents for the task.

    Requires ``task`` to be in serializer ``context``.
    """

    selected_documents = SelectDocumentsField()

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
