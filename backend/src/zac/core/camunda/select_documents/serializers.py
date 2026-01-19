import base64
from dataclasses import dataclass
from datetime import date
from typing import Dict, List

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.catalogi import InformatieObjectType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.concurrent import parallel

from zac.api.context import get_zaak_context
from zac.camunda.user_tasks import Context, usertask_context_serializer
from zac.core.api.serializers import InformatieObjectTypeSerializer
from zac.core.api.validators import validate_zaak_documents
from zac.core.services import create_document, download_document, get_document
from zac.tests.compat import APIModelSerializer
from zgw.models import Zaak

from .utils import get_zaaktype_from_identificatie


@dataclass
class DocumentSelectContext(Context):
    documents_link: str
    informatieobjecttypen: List[InformatieObjectType]


@usertask_context_serializer
class DocumentSelectContextSerializer(APIModelSerializer):
    documents_link = serializers.URLField(
        help_text=_("URL-reference to paginated documents endpoint.")
    )
    informatieobjecttypen = InformatieObjectTypeSerializer(many=True)

    class Meta:
        dataclass = DocumentSelectContext
        fields = (
            "documents_link",
            "informatieobjecttypen",
        )


#
# Write serializer
#


class SelectedDocumentSerializer(serializers.Serializer):
    document = serializers.URLField(
        label=_("selected DOCUMENT"),
        help_text=_("URL-reference of the selected DOCUMENT from the relevant ZAAK."),
        allow_blank=False,
    )

    document_type = serializers.URLField(
        label=_("selected document type"),
        help_text=_("URL-reference of the selected document type."),
        allow_blank=False,
    )


class DocumentSelectTaskSerializer(serializers.Serializer):
    """
    Serializes the selected documents for the task.

    Requires ``task`` to be in serializer ``context``.
    """

    selected_documents = SelectedDocumentSerializer(many=True)
    _documents: List[Document] = []

    def validate_selected_documents(self, selected_docs):
        # Validate selected documents
        doc_urls = [doc["document"] for doc in selected_docs]
        hoofd_zaak = self.get_zaak_from_context()
        validate_zaak_documents(doc_urls, hoofd_zaak)

        # Validated selected document types according to case type
        related_zaaktype = get_zaaktype_from_identificatie(self.context["task"])

        selected_doc_types = [doc["document_type"] for doc in selected_docs]
        invalid_doc_types = [
            doc_type
            for doc_type in selected_doc_types
            if doc_type not in related_zaaktype.informatieobjecttypen
        ]
        if invalid_doc_types:
            raise serializers.ValidationError(
                _(
                    "Selected document types: {invalid_doc_types} are invalid choices based on the related ZAAKTYPE {zaaktype}."
                ).format(
                    invalid_doc_types=invalid_doc_types,
                    zaaktype=related_zaaktype.omschrijving,
                ),
                code="invalid-choice",
            )
        return selected_docs

    def get_zaak_from_context(self) -> Zaak:
        return get_zaak_context(
            self.context["task"], zaak_url_variable="hoofdZaakUrl"
        ).zaak

    def get_process_variables(self) -> Dict:
        """
        Set bijdrage zaak bijlagen
        """
        assert self._documents, "Please run self.on_task_submission() first."

        return {"documenten": [doc.url for doc in self._documents]}

    def on_task_submission(self) -> None:
        """
        Uploads documents on the DRC and sets _documents property.
        """
        assert hasattr(self, "validated_data"), "Serializer is not validated."

        # Get original documents
        with parallel(max_workers=settings.MAX_WORKERS) as executor:
            original_documents = executor.map(
                lambda doc: get_document(doc["document"]),
                self.validated_data["selected_documents"],
            )
        original_documents = {doc.url: doc for doc in original_documents}

        # Get content of documents
        with parallel(max_workers=settings.MAX_WORKERS) as executor:
            original_documents = executor.map(
                lambda doc: download_document(doc),
                [doc for doc_url, doc in original_documents.items()],
            )
        original_documents = list(original_documents)

        # Set document.inhoud to fetched content
        old_documents = {}
        for doc, inhoud in original_documents:
            inhoud = base64.b64encode(inhoud)
            doc.inhoud = inhoud.decode("ascii")
            old_documents[doc.url] = doc

        # Create list of new document data to upload
        new_documents = []
        for new in self.validated_data["selected_documents"]:
            old = old_documents[new["document"]]
            new_documents.append(
                {
                    "informatieobjecttype": new["document_type"],
                    "bronorganisatie": old.bronorganisatie,
                    "creatiedatum": date.today().isoformat(),
                    "titel": old.titel,
                    "auteur": old.auteur,
                    "taal": old.taal,
                    "inhoud": old.inhoud,
                    "formaat": old.formaat,
                    "bestandsnaam": old.bestandsnaam,
                    "ontvangstdatum": date.today().isoformat(),
                    "bestandsomvang": old.bestandsomvang,
                }
            )

        with parallel(max_workers=settings.MAX_WORKERS) as executor:
            documents = executor.map(
                lambda doc: create_document(doc),
                new_documents,
            )

        self._documents = list(documents)
