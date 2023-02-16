import random

import factory

from ..drf_api.serializers import DEFAULT_ES_ZAAKDOCUMENT_FIELDS


def get_random_search_query():
    fields = random.choices(DEFAULT_ES_ZAAKDOCUMENT_FIELDS)
    include_closed = random.choice([False, True])
    return {
        "fields": sorted(fields),
        "include_closed": include_closed,
    }


class SearchReportFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "search-report-%d" % n)
    query = factory.LazyFunction(get_random_search_query)

    class Meta:
        model = "elasticsearch.SearchReport"
