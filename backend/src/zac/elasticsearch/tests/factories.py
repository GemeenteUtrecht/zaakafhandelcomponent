import random
from dataclasses import dataclass
from typing import List

import factory

from ..drf_api.serializers import DEFAULT_ES_FIELDS


def get_random_search_query():
    fields = random.choices(DEFAULT_ES_FIELDS)
    include_closed = random.choice([False, True])
    return {
        "fields": fields,
        "include_closed": include_closed,
    }


class SearchReportFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: "search-report-%d" % n)

    class Meta:
        model = "elasticsearch.SearchReport"

    query = factory.LazyFunction(get_random_search_query)
