import operator
from functools import reduce
from typing import Optional

from django.utils.translation import gettext_lazy as _

from elasticsearch_dsl.query import Query, Range, Term
from rest_framework import serializers
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.api_models.documenten import Document

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.datastructures import VA_ORDER
from zac.accounts.permissions import Blueprint, PermissionObjectType
from zac.core.services import fetch_catalogus
from zgw.models.zrc import Zaak

from .permissions import zaken_handle_access


class ZaakTypeBlueprint(Blueprint):
    catalogus = serializers.CharField(
        help_text=_(
            "On read: `domein` & on write: `url` of CATALOGUS where ZAAKTYPEs are located."
        )
    )
    zaaktype_omschrijving = serializers.CharField(
        max_length=100,
        help_text=_("ZAAKTYPE to which the connected permission applies to"),
    )
    max_va = serializers.ChoiceField(
        choices=VertrouwelijkheidsAanduidingen.choices,
        initial=VertrouwelijkheidsAanduidingen.openbaar,
        help_text=_(
            "Spans ZAAKen until and including this `vertrouwelijkheidaanduiding`."
        ),
    )

    @staticmethod
    def is_zaak_behandelaar(user, zaak: Zaak):
        from .services import get_rollen

        user_rollen = [
            rol
            for rol in get_rollen(zaak)
            if rol.omschrijving_generiek
            in [RolOmschrijving.behandelaar, RolOmschrijving.initiator]
            and rol.betrokkene_type == RolTypes.medewerker
            and user.username.lower()
            in rol.betrokkene_identificatie.get("identificatie", "").lower()
        ]
        return bool(user_rollen)

    def has_access(self, zaak: Zaak, permission: str = None):
        # special case for zaken_handle_access permission:
        if permission == zaken_handle_access.name:
            user = self.context.get("user")

            if not user or not self.is_zaak_behandelaar(user, zaak):
                return False

        zaaktype = zaak.zaaktype
        if isinstance(zaaktype, str):
            from .services import fetch_zaaktype

            zaaktype = fetch_zaaktype(zaaktype)

        if isinstance(zaaktype.catalogus, str):
            from .services import fetch_catalogus

            catalogus = fetch_catalogus(zaaktype.catalogus)

        current_va_order = VA_ORDER[zaak.vertrouwelijkheidaanduiding]
        max_va_order = VA_ORDER[self.data["max_va"]]

        return (
            catalogus.domein == self.data["catalogus"]
            and zaaktype.omschrijving == self.data["zaaktype_omschrijving"]
            and current_va_order <= max_va_order
        )

    def search_query(self, on_nested_field: Optional[str] = "") -> Query:
        catalogus_field = "zaaktype__catalogus_domein"
        omschrijving_field = "zaaktype__omschrijving"
        va_field = "va_order"
        if on_nested_field:
            catalogus_field = f"{on_nested_field}__{catalogus_field}"
            omschrijving_field = f"{on_nested_field}__{omschrijving_field}"
            va_field = f"{on_nested_field}__va_order"

        query = [
            Term(**{catalogus_field: self.data["catalogus"]}),
            Term(**{omschrijving_field: self.data["zaaktype_omschrijving"]}),
            Range(**{va_field: {"lte": VA_ORDER[self.data["max_va"]]}}),
        ]
        return query if on_nested_field else reduce(operator.and_, query)

    def short_display(self):
        return f"{self.data['zaaktype_omschrijving']} ({self.data['max_va']})"

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data["catalogus"] = fetch_catalogus(data["catalogus"]).domein
        return data


class InformatieObjectTypeBlueprint(Blueprint):
    catalogus = serializers.CharField(
        help_text=_(
            "On read: `domein` & on write: `url` of CATALOGUS where ZAAKTYPEs are located."
        )
    )
    iotype_omschrijving = serializers.CharField(
        max_length=100,
        help_text=_(
            "INFORMATIEOBJECTTYPE to which the connected permission applies to"
        ),
    )
    max_va = serializers.ChoiceField(
        choices=VertrouwelijkheidsAanduidingen.choices,
        initial=VertrouwelijkheidsAanduidingen.openbaar,
        help_text=_("Maximum vertrouwelijkheidaanduiding of the INFORMATIEOBJECT"),
    )

    def has_access(self, document: Document, permission: str = None):
        iotype = document.informatieobjecttype
        if isinstance(iotype, str):
            from .services import get_informatieobjecttype

            iotype = get_informatieobjecttype(iotype)

        if isinstance(iotype.catalogus, str):
            from .services import fetch_catalogus

            catalogus = fetch_catalogus(iotype.catalogus)

        current_va_order = VA_ORDER[document.vertrouwelijkheidaanduiding]
        max_va_order = VA_ORDER[self.data["max_va"]]

        return (
            catalogus.domein == self.data["catalogus"]
            and iotype.omschrijving == self.data["iotype_omschrijving"]
            and current_va_order <= max_va_order
        )

    def short_display(self):
        return f"{self.data['iotype_omschrijving']} ({self.data['max_va']})"

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data["catalogus"] = fetch_catalogus(data["catalogus"]).domein
        return data


zaak_object_type = PermissionObjectType(
    name=PermissionObjectTypeChoices.zaak, blueprint_class=ZaakTypeBlueprint
)
document_object_type = PermissionObjectType(
    name=PermissionObjectTypeChoices.document,
    blueprint_class=InformatieObjectTypeBlueprint,
)
