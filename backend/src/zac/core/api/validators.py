from typing import List

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, serializers

from zac.contrib.objects.services import fetch_zaaktypeattributen_objects_for_zaaktype
from zac.core.services import (
    fetch_zaakeigenschappen,
    get_eigenschap,
    get_eigenschappen,
    get_zaak,
    get_zaaktype,
)
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

    if not selected_documents:
        return

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


def validate_zaakeigenschappen(selected_zaakeigenschappen: List[str], zaak: Zaak):
    # Make sure selected documents are unique
    if len((set(selected_zaakeigenschappen))) != len(selected_zaakeigenschappen):
        raise exceptions.ValidationError(
            _("Please select each `ZAAKEIGENSCHAPs` only once."),
            code="invalid-choice",
        )

    if not selected_zaakeigenschappen:
        return

    zeis = fetch_zaakeigenschappen(zaak)
    valid_zeis = [zei.url for zei in zeis]
    invalid_zeis = [url for url in selected_zaakeigenschappen if url not in valid_zeis]

    if invalid_zeis:
        raise exceptions.ValidationError(
            _(
                "Selected ZAAKEIGENSCHAPpen: `{invalid_zeis}` are invalid. Please choose one of the "
                "following ZAAKEIGENSCHAPpen: {valid_zeis}."
            ).format(invalid_zeis=invalid_zeis, valid_zeis=valid_zeis),
            code="invalid-choice",
        )


class ZaakEigenschappenValidator:
    requires_context = True

    def __call__(self, value, serializer_field):
        serializer = serializer_field.parent

        if not hasattr(serializer, "get_zaak_from_context"):
            raise ImproperlyConfigured(
                f"Serializer '{serializer.__class__}' needs a 'get_zaak_from_context' method "
                "to validate the documents."
            )
        zaak = serializer.get_zaak_from_context()
        validate_zaakeigenschappen(value, zaak)


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
        from decimal import Decimal

        zt_attrs = {
            attr["naam"]: attr
            for attr in fetch_zaaktypeattributen_objects_for_zaaktype(
                zaaktype=eigenschap.zaaktype
            )
        }
        if zt_attr := zt_attrs.get(eigenschap.naam):
            if enum := zt_attr.get("enum"):
                if waarde not in enum:
                    # Format waarde for display - if it's a number, format with 2 decimal places
                    display_waarde = waarde
                    try:
                        display_waarde = "{:.2f}".format(Decimal(waarde))
                    except (ValueError, TypeError):
                        pass

                    raise serializers.ValidationError(
                        self.message.format(
                            naam=eigenschap.naam,
                            choices=enum,
                            waarde=display_waarde,
                        )
                    )
        else:
            if (
                eigenschap.specificatie.waardenverzameling
                and waarde not in eigenschap.specificatie.waardenverzameling
            ):
                # Format waarde for display - if it's a number, format with 2 decimal places
                display_waarde = waarde
                try:
                    display_waarde = "{:.2f}".format(Decimal(waarde))
                except (ValueError, TypeError):
                    pass

                raise serializers.ValidationError(
                    self.message.format(
                        naam=eigenschap.naam,
                        choices=eigenschap.specificatie.waardenverzameling,
                        waarde=display_waarde,
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

        # Validate format (getal, tekst, datum, datum_tijd)
        self._validate_format(eigenschap, value)

        # Validate enum/waardenverzameling
        self._validate_waarde_from_spec_or_camunda_forms(eigenschap, value)

        return value

    def _validate_format(self, eigenschap, waarde):
        """Validate that waarde matches the expected format (getal, tekst, datum, datum_tijd)"""
        from decimal import InvalidOperation

        try:
            # Use eigenschap.to_python() to validate the format
            eigenschap.to_python(waarde)
        except (ValueError, AssertionError, AttributeError, InvalidOperation) as e:
            formaat = eigenschap.specificatie.formaat
            if formaat == "getal":
                raise serializers.ValidationError(_("Een geldig nummer is vereist."))
            elif formaat == "datum":
                raise serializers.ValidationError(_("Voer een geldige datum in."))
            elif formaat == "datum_tijd":
                raise serializers.ValidationError(_("Voer een geldige datum/tijd in."))
            else:
                raise serializers.ValidationError(
                    _(
                        "Waarde voldoet niet aan het verwachte formaat: {formaat}"
                    ).format(formaat=formaat)
                )
