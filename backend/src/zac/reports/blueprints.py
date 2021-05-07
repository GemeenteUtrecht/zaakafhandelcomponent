from django.utils.translation import gettext_lazy as _

from elasticsearch_dsl.query import Query, Term
from rest_framework import serializers
from zgw_consumers.concurrent import parallel

from zac.accounts.permissions import Blueprint
from zac.reports.models import Report


class ReportBlueprint(Blueprint):
    zaaktypen = serializers.ListField(
        child=serializers.CharField(max_length=50),
        help_text=_(
            "List of identifications of zaaktypen to which permission is granted."
        ),
    )

    def has_access(self, report: Report):
        return set(report.zaaktypen).issubset(set(self.data["zaaktypen"]))

    def search_query(self) -> Query:
        from zac.core.services import _get_from_catalogus

        with parallel() as executor:
            zaaktypen = executor.map(
                lambda identificatie: _get_from_catalogus(
                    "zaaktype", catalogus="", identificatie=identificatie
                ),
                self.data["zaaktypen"],
            )

        all_zaaktypen = sum(zaaktypen, [])

        url = all_zaaktypen.pop()
        query = Term(zaaktype_url=url)
        for url in all_zaaktypen:
            query |= Term(zaaktype_url=url)
        return query

    def short_display(self):
        return f"{self.data['zaaktypen']}"
