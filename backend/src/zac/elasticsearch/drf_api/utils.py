from collections import OrderedDict
from typing import Any, Dict, Iterator, Tuple, Optional

from drf_spectacular.openapi import OpenApiParameter
from elasticsearch_dsl import Document, field





def get_sorting_fields(fields: Dict[str, Any]) -> Iterator[Tuple[str, str]]:
    """
    This (recursively) lists all the (nested) fields that can be sorted on.

    """
    fields = OrderedDict(fields)
    for field_name, field_value in fields.items():
        field_type = field_value["type"]
        if field_type == "nested":
            nested_fields = get_sorting_fields(field_value["properties"])
            for nested_field_name, nested_field_value in list(nested_fields):
                yield (f"{field_name}.{nested_field_name}", nested_field_value)

        elif field == "object":
            continue

        else:
            yield (field_name, field_type)


def get_document_properties(es_document: Document) -> Optional[Dict[str, Any]]:
    assert isinstance(
        es_document(), Document
    ), f"Expected object of type elasticsearch_dsl.Document but got {type(es_document)} instead."
    properties = es_document._doc_type.mapping.properties.to_dict().get("properties")
    return properties


def es_document_to_sorting_parameters(
    es_document: Document,
) -> OpenApiParameter:
    """
    Turns the ES Document fields to possible sorting parameters.

    """
    properties = get_document_properties(es_document)
    if not properties:
        return None

    else:
        enum = [field[0] for field in get_sorting_fields(properties)]
        return OpenApiParameter(
            name="sorting",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Possible sorting parameters. Multiple values are possible and should be separated by a comma.",
            enum=enum,
        )
