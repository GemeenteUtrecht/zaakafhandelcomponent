from rest_framework import fields

from zac.utils.filters import ApiFilterSet


class ZaaktypenFilterSet(ApiFilterSet):
    q = fields.CharField(
        required=False, help_text="`icontains` on `omschrijving` field"
    )

    def filter_q(self, queryset, value) -> list:
        return [
            zaaktype
            for zaaktype in queryset
            if value.lower() in zaaktype["omschrijving"].lower()
        ]


class EigenschappenFilterSet(ApiFilterSet):
    # filtering is done in viewset.get_queryset() method.
    # This filterset is used just to validate query params
    zaaktype_omschrijving = fields.CharField()
    catalogus = fields.URLField()
