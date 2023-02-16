from typing import List

from rest_framework.response import Response

from zac.core.api.pagination import BffPagination

from .serializers import DEFAULT_ES_ZAAKDOCUMENT_FIELDS


class ESPagination(BffPagination):
    def get_paginated_response(self, data, fields: List[str]):
        return Response(
            {
                "fields": fields,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "count": self.page.paginator.count,
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        schema = super().get_paginated_response_schema(schema)
        schema["properties"]["fields"] = {
            "type": "array",
            "items": "string",
            "nullable": False,
            "default": DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
        }
        return schema
