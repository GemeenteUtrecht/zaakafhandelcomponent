from dataclasses import dataclass
from datetime import date
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.concurrent import parallel
from zgw_consumers.drf.serializers import APIModelSerializer
from zgw_consumers.service import get_paginated_results

from zac.api.context import get_zaak_context
from zac.camunda.user_tasks import Context, usertask_context_serializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.fields import DowcUrlFieldReadOnly
from zac.core.api.validators import validate_zaak_documents
from zac.core.models import CoreConfig
from zac.core.services import _client_from_url, get_documenten


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
        self.zaak = self.get_zaak_from_context()

        # Validate selected documents
        doc_urls = [doc["document"] for doc in selected_docs]
        validate_zaak_documents(doc_urls, self.zaak)

        # Validated selected document types according to case type
        ztc_client = _client_from_url(self.zaak.zaaktype)
        results = get_paginated_results(ztc_client, "informatieobjecttype")
        valid_eiots = [iot["url"] for iot in results]

        selected_doc_types = [doc["document_type"] for doc in selected_docs]
        invalid_doc_types = [
            doc_type for doc_type in selected_doc_types if doc_type not in valid_eiots
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

    def get_zaak_from_context(self):
        zaak_context = get_zaak_context(self.context["task"])
        return zaak_context.zaak

    def get_process_variables(self) -> Dict:
        """
        Set bijdrage zaak bijlagen
        """
        assert self._documents, "Please run self.on_task_submission() first."

        return {"bijdragezaakBijlagen": [doc["url"] for doc in self._documents]}

    def on_task_submission(self) -> None:
        """
        Uploads documents on the DRC and sets _documents property.
        """
        assert hasattr(self, "validated_data"), "Serializer is not validated."

        original_documents, gone = get_documenten(self.get_zaak_from_context())

        upload = []
        for old, new in zip(
            original_documents, self.validated_data["selected_documents"]
        ):
            upload.append(
                {
                    "informatieobjecttype": new["document_type"],
                    "bronorganisatie": self.zaak.bronorganisatie,
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
