from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.catalogi import InformatieObjectType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.concurrent import parallel
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.context import get_zaak_context
from zac.camunda.data import ProcessInstance
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks import Context, usertask_context_serializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.fields import DowcUrlFieldReadOnly
from zac.core.api.serializers import InformatieObjectTypeSerializer
from zac.core.api.validators import validate_zaak_documents
from zac.core.models import CoreConfig
from zac.core.services import fetch_zaaktype, get_documenten
from zgw.models import Zaak


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
    informatieobjecttypen: List[InformatieObjectType]


@usertask_context_serializer
class DocumentSelectContextSerializer(APIModelSerializer):
    documents = DocumentSerializer(many=True)
    informatieobjecttypen = InformatieObjectTypeSerializer(many=True)

    class Meta:
        model = DocumentSelectContext
        fields = (
            "documents",
            "informatieobjecttypen",
        )


#
# Write serializer
#


class SelectedDocumentSerializer(serializers.Serializer):
    document = serializers.URLField(
        label=_("Selected document"),
        help_text=_("The URL of the selected document from the relevant case."),
        allow_blank=False,
    )

    document_type = serializers.URLField(
        label=_("Selected document type"),
        help_text=_("The URL of the selected document type."),
        allow_blank=False,
    )


class DocumentSelectTaskSerializer(serializers.Serializer):
    """
    Serializes the selected documents for the task.

    Requires ``task`` to be in serializer ``context``.
    """

    selected_documents = SelectedDocumentSerializer(many=True)
    _documents: List = []

    def validate_selected_documents(self, selected_docs):
        # Validate selected documents
        hoofd_zaak = self.get_zaak_from_context()
        doc_urls = [doc["document"] for doc in selected_docs]
        validate_zaak_documents(doc_urls, hoofd_zaak)

        # Validated selected document types according to case type
        process_instance = self._get_process_instance()
        related_zaaktype_url = process_instance.get_variable("zaaktype")
        related_zaaktype = fetch_zaaktype(related_zaaktype_url)

        selected_doc_types = [doc["document_type"] for doc in selected_docs]
        invalid_doc_types = [
            doc_type
            for doc_type in selected_doc_types
            if doc_type not in related_zaaktype.informatieobjecttypen
        ]
        if invalid_doc_types:
            raise serializers.ValidationError(
                _(
                    "Selected document types: {invalid_doc_types} are invalid choices."
                ).format(
                    invalid_doc_types=invalid_doc_types,
                ),
                code="invalid-choice",
            )
        return selected_docs

    def _get_process_instance(self) -> Optional[ProcessInstance]:
        try:
            return self._process_instance
        except AttributeError:
            self._process_instance = get_process_instance(
                self.context["task"].process_instance_id
            )
            if not self._process_instance:
                raise serializers.ValidationError(
                    _(
                        "No process instance with id: {pid} was found.".format(
                            pid=self.context["task"].process_instance_id
                        )
                    )
                )

        return self._process_instance

    def get_zaak_from_context(self) -> Zaak:
        try:
            return self._hoofd_zaak
        except AttributeError:
            self._hoofd_zaak = get_zaak_context(self.context["task"]).zaak

        return self._hoofd_zaak

    def get_process_variables(self) -> Dict:
        """
        Set bijdrage zaak bijlagen
        """
        assert self._documents, "Please run self.on_task_submission() first."

        return {"documenten": [doc["url"] for doc in self._documents]}

    def on_task_submission(self) -> None:
        """
        Uploads documents on the DRC and sets _documents property.
        """
        assert hasattr(self, "validated_data"), "Serializer is not validated."

        original_documents, gone = get_documenten(self.get_zaak_from_context())
        upload = []
        process_instance = self._get_process_instance()
        for old, new in zip(
            original_documents, self.validated_data["selected_documents"]
        ):
            upload.append(
                {
                    "informatieobjecttype": new["document_type"],
                    "bronorganisatie": process_instance.get_variable("bronorganisatie"),
                    "creatiedatum": date.today().isoformat(),
                    "titel": old.titel,
                    "auteur": old.auteur,
                    "taal": old.taal,
                    "inhoud": old.inhoud,
                    "formaat": old.formaat,
                    "bestandsnaam": old.bestandsnaam,
                    "ontvangstdatum": date.today().isoformat(),
                }
            )

        core_config = CoreConfig.get_solo()
        service = core_config.primary_drc
        if not service:
            raise RuntimeError("No DRC configured!")

        drc_client = service.build_client()
        with parallel() as executor:
            documents = executor.submit(
                lambda doc: drc_client.create("enkelvoudiginformatieobject", doc),
                upload,
            )

        self._documents = documents.result()
