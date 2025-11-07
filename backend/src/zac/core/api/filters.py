from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, fields, serializers

from zac.core.services import get_catalogi
from zac.utils.filters import ApiFilterSet


class ZaaktypenFilterSet(ApiFilterSet):
    q = fields.CharField(
        required=False, help_text=_("`icontains` on `omschrijving` field")
    )
    domein = fields.CharField(
        required=False,
        help_text=_("`iexact` on `domein` field of CATALOGUS related to ZAAKTYPEs."),
    )
    active = fields.BooleanField(
        default=False,
        help_text=_("If `True` only show the active versions of ZAAKTYPEs."),
    )

    def validate_domein(self, domein):
        catalogi = get_catalogi()
        catalogus = [cat for cat in catalogi if cat.domein.lower() == domein.lower()]
        if not catalogus:
            raise serializers.ValidationError(
                _("Could not find a CATALOGUS with `domein`: `{val}`.").format(
                    val=domein
                )
            )
        return domein

    def filter_q(self, results, value) -> list:
        return [
            zaaktype
            for zaaktype in results
            if value.lower() in zaaktype.omschrijving.lower()
        ]

    def filter_domein(self, results, value) -> list:
        catalogi = get_catalogi()
        catalogus = [cat for cat in catalogi if cat.domein.lower() == value.lower()]
        return [
            zaaktype
            for zaaktype in results
            if zaaktype.catalogus.url == catalogus[0].url
        ]

    def filter_active(self, results, value) -> list:
        if value:
            return [zt for zt in results if not zt.einde_geldigheid]
        return results


class EigenschappenFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_queryset() method.
    # This filterset is used just to validate query params
    zaaktype = fields.URLField(
        required=False, help_text=_("URL-reference of related ZAAKTYPE.")
    )
    zaaktype_identificatie = fields.CharField(
        required=False,
        help_text=_(
            "`identificatie` of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE."
        ),
    )
    catalogus = fields.URLField(
        required=False, help_text=_("URL-reference of related CATALOGUS.")
    )

    def validate(self, data):
        zt = self.data.get("zaaktype")
        zti = self.data.get("zaaktype_identificatie")
        cat = self.data.get("catalogus")

        if zt:
            if zti or cat:
                raise exceptions.ValidationError(
                    _(
                        "ZAAKTYPE is mutually exclusive from (`zaaktype_identificatie` and CATALOGUS)."
                    )
                )
        elif not (zti and cat):
            raise exceptions.ValidationError(
                _(
                    "The CATALOGUS and `zaaktype_identificatie` are both required if one is given."
                )
            )
        return data


class ZaakEigenschappenFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_object() method.
    # This filterset is used just to validate query params
    url = fields.URLField(
        required=True, help_text=_("URL-reference of ZAAKEIGENSCHAP in ZAKEN API.")
    )


class ZaakObjectFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_object() method.
    # This filterset is used just to validate query params
    url = fields.URLField(
        required=True, help_text=_("URL-reference of ZAAKOBJECT in ZAKEN API.")
    )


class ZaakRolFilterSet(ApiFilterSet):
    url = fields.URLField(
        required=True, help_text=_("URL-reference to ROL in ZAKEN API.")
    )


class ObjectTypeFilterSet(ApiFilterSet):
    zaaktype = fields.URLField(
        required=False, help_text=_("URL-reference to ZAAKTYPE in CATALOGI API.")
    )
