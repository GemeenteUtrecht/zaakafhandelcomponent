from django.utils.translation import ugettext_lazy as _

from rest_framework import exceptions, fields

from zac.utils.filters import ApiFilterSet


class ZaaktypenFilterSet(ApiFilterSet):
    q = fields.CharField(
        required=False, help_text="`icontains` on `omschrijving` field"
    )

    def filter_q(self, results, value) -> list:
        return [
            zaaktype
            for zaaktype in results
            if value.lower() in zaaktype.omschrijving.lower()
        ]


class EigenschappenFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_queryset() method.
    # This filterset is used just to validate query params
    zaaktype = fields.URLField(
        required=False, help_text=_("URL-reference of related ZAAKTYPE")
    )
    zaaktype_identificatie = fields.CharField(
        required=False,
        help_text=_(
            "`identificatie` of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE."
        ),
    )
    catalogus = fields.URLField(
        required=False, help_text=_("URL-reference of related CATALOGUS")
    )

    def is_valid(self):
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
        return super().is_valid()


class ZaakEigenschappenFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_object() method.
    # This filterset is used just to validate query params
    url = fields.URLField(
        required=True, help_text=_("URL-reference of ZAAKEIGENSCHAP in ZAKEN API")
    )


class ZaakObjectFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_object() method.
    # This filterset is used just to validate query params
    url = fields.URLField(
        required=True, help_text=_("URL-reference of ZAAKOBJECT in ZAKEN API")
    )
