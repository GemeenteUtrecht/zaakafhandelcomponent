from typing import Dict, List, Optional

from django.core.exceptions import ImproperlyConfigured

from elasticsearch_dsl import Document, field
from rest_framework import views
from rest_framework.request import Request
from rest_framework.settings import api_settings

from .utils import get_document_fields, get_document_properties


class ESOrderingFilter:
    """
    A custom filter that is strongly inspired by the rest_framework ordering filter
    and has a similar interface. It can be used with the 'Document' class of elasticsearch_dsl
    library.

    For performance reasons text fields are kept as unsortable unless they include a
    keywords subfield. The filter will omit any 'Text' fields as sortable field
    candidates if they are non-compliant.

    Note: in this filter ordering = None is the same as ordering = "__all__".

    """

    ordering_param = api_settings.ORDERING_PARAM
    ordering_fields = None

    def _check_text_field_for_keyword_field_in_fields_attr(
        self, es_document: Document, field_name: str
    ):
        # We are checking if we need to add keyword to the field name here
        # because this method is called right before we interact with
        # the ES interface and in the current implementation the ES
        # interface requires that a text field should include a
        # 'fields' key with a keyword field that we can sort on IF we
        # want to sort on that field.

        properties = get_document_properties(es_document)
        for name in field_name.split("."):
            properties = properties.get("properties")
            if properties:
                properties = properties.get(name, {})

        # Properties is reduced to the values of the field.
        # If the field is a text field, has a 'fields' key and
        # fields contains 'keyword', add keyword to the field name.
        # If it doesn't it shouldn't have made it this far
        # and it should throw an exception.
        if properties:
            if properties.get("type") == field.Text.name:
                # Throw an exception if invalid
                properties["fields"][field.Keyword.name]
                return f"{field_name}.{field.Keyword.name}"

        return field_name

    def _add_keywords(self, ordering: List[str], view: views.APIView) -> List[str]:
        """
        Fields that have a 'text' field type could still be searchable if they have a keyword field in their fields attribute.

        This adds .keyword to those fields.

        """

        final_ordering = []
        for field_name in ordering:
            reverse = field_name.startswith("-")
            field_name = self._check_text_field_for_keyword_field_in_fields_attr(
                view.search_document, field_name[1 if reverse else 0 :]
            )
            if reverse:
                field_name = f"-{field_name}"
            final_ordering.append(field_name)

        return final_ordering

    def get_ordering(
        self, request: Request, view: views.APIView
    ) -> Optional[List[str]]:
        """
        Ordering is set by a comma delimited ?ordering=... query parameter.

        The `ordering` query parameter can be overridden by
        specifying an `ORDERING_PARAM` value in the API settings.

        """
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(",")]
            ordering = self.remove_invalid_fields(fields, view)
            ordering = self._add_keywords(ordering, view)
            if ordering:
                return ordering

        return self.get_default_ordering(view)

    def get_default_ordering(self, view: views.APIView) -> Optional[List[str]]:
        return getattr(view, "ordering", None)

    def get_all_fields(self, view: views.APIView) -> Dict[str, str]:
        # If `ordering_fields` is not specified, then we determine a default
        # based on the serializer class, if one exists on the view.
        try:
            search_document = view.search_document

        except AttributeError:
            msg = (
                "Cannot use %s on a view which does not have a "
                "'search_document' attribute."
            )
            raise ImproperlyConfigured(msg % self.__class__.__name__)

        properties = get_document_properties(search_document)
        properties = properties.get("properties", None)
        if properties:
            return {
                field_name: field_type
                for field_name, field_type in get_document_fields(
                    properties, sortable=True
                )
            }

        return dict()

    def get_ordering_fields(self, view: views.APIView) -> Dict[str, str]:
        ordering_fields = getattr(view, "ordering_fields", self.ordering_fields)
        all_fields = self.get_all_fields(view)

        if ordering_fields in [None, "__all__"]:
            return all_fields

        return {field_name: all_fields[field_name] for field_name in ordering_fields}

    def remove_invalid_fields(self, fields, view: views.APIView) -> List[str]:
        """
        Fields that have as type 'object' are unsortable for now.

        """
        valid_fields = self.get_ordering_fields(view)

        def term_valid(term):
            if term.startswith("-"):
                term = term[1:]
            return (term in valid_fields) and (valid_fields[term] != field.Object.name)

        return [term for term in fields if term_valid(term)]
