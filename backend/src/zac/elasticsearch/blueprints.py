from django.utils.translation import gettext_lazy as _

from elasticsearch_dsl.query import Query, Term
from rest_framework import serializers
from zgw_consumers.concurrent import parallel

from zac.accounts.permissions import Blueprint
from zac.elasticsearch.models import SearchReport
from zac.elasticsearch.searches import search


class SearchReportBlueprint(Blueprint):
    zaaktypen = serializers.ListField(
        child=serializers.CharField(max_length=50),
        help_text=_(
            "List of identifications of zaaktypen to which permission is granted."
        ),
    )

    def has_access(self, search_report: SearchReport):
        es_query = search_report.query
        no_fields = {**es_query}

        # Remove fields parameter of search as it's not required for these purposes
        if "fields" in no_fields:
            no_fields.pop("fields")

        es_results = search(user=self.context["user"], **no_fields)
        zaaktypen_in_report = [result.zaaktype.url for result in es_results]
        return set(zaaktypen_in_report).issubset(set(self.data["zaaktypen"]))

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
