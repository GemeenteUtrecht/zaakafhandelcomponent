from typing import List

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions

from zac.core.services import get_documenten
from zgw.models.zrc import Zaak


def validate_zaak_documents(selected_documents: List[str], zaak: Zaak):
    documents, _gone = get_documenten(zaak)

    # Make sure selected documents are unique
    if len((set(selected_documents))) != len(selected_documents):
        raise exceptions.ValidationError(
            _("Please select each document only once."),
            code="invalid-choice",
        )

    valid_docs = [doc.url for doc in documents]
    invalid_docs = [url for url in selected_documents if url not in valid_docs]

    if invalid_docs:
        raise exceptions.ValidationError(
            _(
                "Selected documents: {invalid_docs} are invalid. Please choose one of the "
                "following documents: {valid_docs}."
            ).format(invalid_docs=invalid_docs, valid_docs=valid_docs),
            code="invalid-choice",
        )


class ZaakDocumentsValidator:
    requires_context = True

    def __call__(self, value, serializer_field):
        serializer = serializer_field.parent

        if not hasattr(serializer, "get_zaak_from_context"):
            raise ImproperlyConfigured(
                f"Serializer '{serializer.__class__}' needs a 'get_zaak_from_context' method "
                "to validate the documents."
            )
        zaak = serializer.get_zaak_from_context()
        validate_zaak_documents(value, zaak)
