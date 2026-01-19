from collections import OrderedDict
from typing import Any, Dict, Iterator, Optional, Tuple

from django.utils.translation import gettext_lazy as _

from drf_spectacular.openapi import OpenApiParameter
from elasticsearch_dsl import Document, field


def get_document_fields(
    fields: Dict[str, Any], sortable: bool = False
) -> Iterator[Tuple[str, str]]:
    """
    This (recursively) lists all the (nested) fields that can be sorted on.

    A 'Text' field without a 'fields' key is NOT a sortable field.
    """
    fields = OrderedDict(fields)
    for field_name, field_value in fields.items():
        field_type = field_value["type"]
        if field_type in [field.Nested.name, field.Object.name]:
            properties = field_value.get("properties")
            if properties:
                nested_fields = get_document_fields(properties, sortable=sortable)
                for nested_field_name, nested_field_value in list(nested_fields):
                    yield (f"{field_name}.{nested_field_name}", nested_field_value)

        else:
            if sortable and field_type == field.Text.name:
                try:
                    field_value["fields"][field.Keyword.name]
                    yield (field_name, field_type)
                except KeyError:
                    # In this case the field is not sortable for now - skip it.

                    # We're not adding keyword to the name yet because that doesn't make
                    # sense at this stage. This function just spits back
                    # the valid ordering fields.
                    pass
            else:
                yield (field_name, field_type)


def get_document_properties(es_document: Document) -> Optional[Dict[str, Any]]:
    assert isinstance(
        es_document(), Document
    ), f"Expected object of type elasticsearch_dsl.Document but got {type(es_document)} instead."
    properties = es_document._doc_type.mapping.properties.to_dict()
    return properties


def es_document_to_ordering_parameters(
    es_document: Document,
) -> OpenApiParameter:
    """
    Turns the ES Document fields to possible ordering parameters.

    """
    properties = get_document_properties(es_document)
    properties = properties.get("properties", None)
    if not properties:
        return None

    else:
        enum = [field[0] for field in get_document_fields(properties, sortable=True)]
        return OpenApiParameter(
            name="ordering",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description=_(
                "Possible ordering parameters. Multiple values are possible and should be separated by a comma."
            ),
            enum=enum,
        )
