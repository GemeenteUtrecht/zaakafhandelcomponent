from collections.abc import MutableMapping as Map
from copy import deepcopy
from typing import Any, Dict, List

from requests_mock import Mocker
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType
from zgw_consumers.api_models.documenten import Document


def update_keys(data, update):
    for key in update:
        if key in data and isinstance(data[key], Map) and isinstance(update[key], Map):
            data[key] = update_keys(data[key], update[key])
        else:
            data[key] = update[key]
    return data


def update_dictionary_from_kwargs(data, kwargs):
    to_update = []
    delete_keys = []
    for k, v in kwargs.items():
        if keys := k.split("__"):
            new_v = deepcopy(v)
            for _k in reversed(keys):
                new_v = {_k: new_v}
            to_update.append(new_v)
            delete_keys.append(k)
    for k in delete_keys:
        del kwargs[k]
    for update_updated in to_update:
        update_keys(kwargs, update_updated)
    update_keys(data, kwargs)
    return data


def mock_resource_get(m: Mocker, resource: dict) -> None:
    m.get(resource["url"], json=resource)


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
        iot["url"]: factory(InformatieObjectType, iot) for iot in informatieobjecttypen
    }

    # resolve relations
    for document in documenten_obj:
        document.informatieobjecttype = informatieobjecttypen[
            document.informatieobjecttype
        ]

    return documenten_obj
