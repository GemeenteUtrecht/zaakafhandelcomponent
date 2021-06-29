from typing import Dict, List

from rest_framework.response import Response

from zac.core.api.pagination import BffPagination

from ..documents import ZaakDocument
from .utils import get_document_fields, get_document_properties


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
