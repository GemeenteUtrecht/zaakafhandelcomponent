from typing import List, Optional

from rest_framework.response import Response
from rest_framework.views import APIView

from zac.core.api.pagination import BffPagination

from .utils import get_document_fields, get_document_properties


class ESPagination(BffPagination):
    def __init__(self, view: Optional[APIView] = None):
        self.view = view

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

        default_fields = (
            [
                field[0]
                for field in get_document_fields(
                    get_document_properties(self.view.search_document)["properties"]
                )
            ]
            if self.view
            else []
        )

        schema["properties"]["fields"] = {
            "type": "array",
            "items": {"type": "string"},
            "nullable": False,
            "default": default_fields,
        }
        return schema
