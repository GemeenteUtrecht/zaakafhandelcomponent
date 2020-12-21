from typing import Any, Dict, List

from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document

from zgw.models import InformatieObjectType


def paginated_response(results: List[dict]) -> Dict[str, Any]:
    body = {
        "count": len(results),
        "previous": None,
        "next": None,
        "results": results,
    }
    return body


def make_document_objects(
    documents: List[Dict], informatieobjecttypen: List[Dict]
) -> List[Document]:
    documenten_obj = factory(Document, documents)

    # Make objects for all informatieobjecttypen
    informatieobjecttypen = {
        iot["url"]: InformatieObjectType.from_raw(iot) for iot in informatieobjecttypen
    }

    # resolve relations
    for document in documenten_obj:
        document.informatieobjecttype = informatieobjecttypen[
            document.informatieobjecttype
        ]

    return documenten_obj
