from django.utils.translation import ugettext_lazy as _

from rest_framework import fields

from zac.utils.filters import ApiFilterSet


class ZaaktypenFilterSet(ApiFilterSet):
    q = fields.CharField(
        required=False, help_text="`icontains` on `omschrijving` field"
    )

    def filter_q(self, results, value) -> list:
        return [
            zaaktype
            for zaaktype in results
            if value.lower() in zaaktype["omschrijving"].lower()
        ]


class EigenschappenFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_queryset() method.
    # This filterset is used just to validate query params
    zaaktype_omschrijving = fields.CharField(
        help_text=_(
            "Description of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE"
        )
    )
    catalogus = fields.URLField(help_text=_("Url reference of related CATALOGUS"))


class ZaakEigenschappenFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_object() method.
    # This filterset is used just to validate query params
    url = fields.URLField(
        required=True, help_text=_("URL reference of ZAAK EIGENSCHAP in ZAKEN API")
    )


class ZaakObjectFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_object() method.
    # This filterset is used just to validate query params
    url = fields.URLField(
        required=True, help_text=_("URL reference of ZAAK OBJECT in ZAKEN API")
    )
