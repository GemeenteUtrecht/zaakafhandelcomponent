from typing import List

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, serializers

from zac.contrib.objects.services import fetch_zaaktypeattributen_objects_for_zaaktype
from zac.core.services import get_eigenschap, get_eigenschappen, get_zaak, get_zaaktype
from zac.elasticsearch.searches import search_informatieobjects
from zgw.models.zrc import Zaak

from .constants import ACCEPTABLE_CONTENT_TYPES, RE_PROG


def validate_zaak_documents(selected_documents: List[str], zaak: Zaak):
    # Make sure selected documents are unique
    if len((set(selected_documents))) != len(selected_documents):
        raise exceptions.ValidationError(
            _("Please select each document only once."),
            code="invalid-choice",
        )

    documents = search_informatieobjects(
        zaak=zaak.url, urls=selected_documents, size=len(selected_documents)
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


class ZaakFileValidator:
    def __call__(self, value):
        if not RE_PROG.search(value.name):
            raise exceptions.ValidationError(
                "Only alphanumerical characters, whitespaces, -_() and 1 file extension are allowed."
            )

        if value.content_type.lower() not in ACCEPTABLE_CONTENT_TYPES.values():
            raise exceptions.ValidationError(
                f"File format not allowed. Please use one of the following file formats: {', '.join(ACCEPTABLE_CONTENT_TYPES)}."
            )
        return value


class EigenschapKeuzeWaardeValidator:
    requires_context = True
    message = _(
        "ZAAKEIGENSCHAP with `naam`: `{naam}` must take a value from `{choices}`. Given `waarde`: `{waarde}`."
    )

    def _validate_waarde_from_spec_or_camunda_forms(self, eigenschap, waarde):
        zt_attrs = {
            attr["naam"]: attr
            for attr in fetch_zaaktypeattributen_objects_for_zaaktype(
                zaaktype=eigenschap.zaaktype
            )
        }
        if zt_attr := zt_attrs.get(eigenschap.naam):
            if enum := zt_attr.get("enum"):
                if waarde not in enum:
                    raise serializers.ValidationError(
                        self.message.format(
                            naam=eigenschap.naam,
                            choices=enum,
                            waarde=waarde,
                        )
                    )
        else:
            if (
                eigenschap.specificatie.waardenverzameling
                and waarde not in eigenschap.specificatie.waardenverzameling
            ):
                raise serializers.ValidationError(
                    self.message.format(
                        naam=eigenschap.naam,
                        choices=eigenschap.specificatie.waardenverzameling,
                        waarde=waarde,
                    )
                )

    def __call__(self, value, field: serializers.Field):
        if not (instance := getattr(field.parent, "instance", None)):
            data = field.parent.initial_data
            naam = data["naam"]
            zaak = get_zaak(zaak_url=data["zaak_url"])
            zaaktype = get_zaaktype(zaak.zaaktype)
            eigenschappen = get_eigenschappen(zaaktype)
            try:
                eigenschap = next(
                    (
                        eigenschap
                        for eigenschap in eigenschappen
                        if eigenschap.naam == naam
                    )
                )
            except StopIteration:
                raise serializers.ValidationError(
                    _(
                        "EIGENSCHAP with `naam`: `{naam}` not found for ZAAKTYPE with `omschrijving`: `{omschrijving}` of ZAAK with `identificatie`: `{identificatie}`."
                    ).format(
                        naam=naam,
                        omschrijving=zaaktype.omschrijving,
                        identificatie=zaak.identificatie,
                    )
                )

            eigenschap.zaaktype = zaaktype

        else:
            eigenschap = (
                get_eigenschap(instance.eigenschap)
                if isinstance(instance.eigenschap, str)
                else instance.eigenschap
            )
            eigenschap.zaaktype = (
                get_zaaktype(eigenschap.zaaktype)
                if isinstance(eigenschap.zaaktype, str)
                else eigenschap.zaaktype
            )

        self._validate_waarde_from_spec_or_camunda_forms(eigenschap, value)

        return value
