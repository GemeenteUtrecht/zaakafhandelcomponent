from dataclasses import dataclass
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.context import get_zaak_context
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url


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

    selected_documents = serializers.ListField(
        child=serializers.URLField(),
        label=_("Selecteer de relevante documenten"),
        help_text=_(
            "Dit zijn de documenten die bij de zaak horen. Selecteer de relevante "
            "documenten."
        ),
    )

    def validate_selected_documents(self, selected_documents):
        # Make sure selected documents are unique
        selected_documents = list(dict.fromkeys(selected_documents))

        # Get zaak documents to verify valid document selection
        zaak_context = get_zaak_context(self.context["task"], require_documents=True)
        valid_docs = [doc.url for doc in zaak_context.documents]
        invalid_docs = [doc for doc in selected_documents if not doc in valid_docs]
        if invalid_docs:
            raise serializers.ValidationError(
                _(
                    "Selected documents: {invalid_docs} are invalid. Please choose one of the "
                    "following documents: {valid_docs}."
                ).format(invalid_docs=invalid_docs, valid_docs=valid_docs),
                code="invalid_choice",
            )

        return selected_documents

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
