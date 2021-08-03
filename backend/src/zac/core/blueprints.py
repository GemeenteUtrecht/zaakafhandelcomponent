from django.utils.translation import ugettext_lazy as _

from elasticsearch_dsl.query import Query, Range, Term
from rest_framework import serializers
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.datastructures import VA_ORDER
from zac.accounts.permissions import Blueprint, PermissionObjectType
from zgw.models.zrc import Zaak

from .permissions import zaken_handle_access


class ZaakTypeBlueprint(Blueprint):
    catalogus = serializers.URLField(
        help_text=_("Catalog where zaaktypen are located"),
    )
    zaaktype_omschrijving = serializers.CharField(
        max_length=100,
        help_text=_("Zaaktype to which the connected permission applies to"),
    )
    max_va = serializers.ChoiceField(
        choices=VertrouwelijkheidsAanduidingen.choices,
        initial=VertrouwelijkheidsAanduidingen.openbaar,
        help_text=_(
            "Spans Zaken until and including this vertrouwelijkheidaanduiding."
        ),
    )

    @staticmethod
    def is_zaak_behandelaar(user, zaak: Zaak):
        from .services import get_rollen

        user_rollen = [
            rol
            for rol in get_rollen(zaak)
            if rol.omschrijving_generiek == "behandelaar"
            and rol.betrokkene_type == "medewerker"
            and rol.betrokkene_identificatie.get("identificatie") == user.username
        ]
        return bool(user_rollen)

    def has_access(self, zaak: Zaak, permission: str = None):
        # special case for zaken_handle_access permission:
        if permission == zaken_handle_access.name:
            user = self.context.get("user")

            if not user or self.is_zaak_behandelaar(user, zaak):
                return False

        zaaktype = zaak.zaaktype
        if isinstance(zaaktype, str):
            from .services import fetch_zaaktype

            zaaktype = fetch_zaaktype(zaaktype)

        current_va_order = VA_ORDER[zaak.vertrouwelijkheidaanduiding]
        max_va_order = VA_ORDER[self.data["max_va"]]

        return (
            zaaktype.catalogus == self.data["catalogus"]
            and zaaktype.omschrijving == self.data["zaaktype_omschrijving"]
            and current_va_order <= max_va_order
        )

    def search_query(self) -> Query:
        max_va_order = VA_ORDER[self.data["max_va"]]

        query = (
            Term(zaaktype__catalogus=self.data["catalogus"])
            & Term(zaaktype__omschrijving=self.data["zaaktype_omschrijving"])
            & Range(va_order={"lte": max_va_order})
        )
        return query

    def short_display(self):
        return f"{self.data['zaaktype_omschrijving']} ({self.data['max_va']})"


class InformatieObjectTypeBlueprint(Blueprint):
    catalogus = serializers.URLField(
        help_text=_("Catalog where informatieobjecttypen are located"),
    )
    iotype_omschrijving = serializers.CharField(
        max_length=100,
        help_text=_(
            "Informatieobjecttype to which the connected permission applies to"
        ),
    )
    max_va = serializers.ChoiceField(
        choices=VertrouwelijkheidsAanduidingen.choices,
        initial=VertrouwelijkheidsAanduidingen.openbaar,
        help_text=_("Maximum confidential level of the informatieobject"),
    )

    def has_access(self, document: Document, permission: str = None):
        iotype = document.informatieobjecttype
        if isinstance(iotype, str):
            from .services import get_informatieobjecttype

            iotype = get_informatieobjecttype(iotype)

        current_va_order = VA_ORDER[document.vertrouwelijkheidaanduiding]
        max_va_order = VA_ORDER[self.data["max_va"]]

        return (
            iotype.catalogus == self.data["catalogus"]
            and iotype.omschrijving == self.data["iotype_omschrijving"]
            and current_va_order <= max_va_order
        )

    def short_display(self):
        return f"{self.data['iotype_omschrijving']} ({self.data['max_va']})"


zaak_object_type = PermissionObjectType(
    name=PermissionObjectTypeChoices.zaak, blueprint_class=ZaakTypeBlueprint
)
document_object_type = PermissionObjectType(
    name=PermissionObjectTypeChoices.document,
    blueprint_class=InformatieObjectTypeBlueprint,
)
