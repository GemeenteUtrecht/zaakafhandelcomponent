from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError

from zac.core.services import get_documenten


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
        documents, _gone = get_documenten(zaak)

        # Make sure selected documents are unique
        selected = list(set(value))
        valid_docs = [doc.url for doc in documents]
        invalid_docs = [url for url in selected if url not in valid_docs]

        if invalid_docs:
            raise ValidationError(
                _(
                    "Selected documents: {invalid_docs} are invalid. Please choose one of the "
                    "following documents: {valid_docs}."
                ).format(invalid_docs=invalid_docs, valid_docs=valid_docs),
                code="invalid_choice",
            )
