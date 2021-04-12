from typing import Dict, List, Optional

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from elasticsearch_dsl import field
from rest_framework import views
from rest_framework.request import Request
from rest_framework.settings import api_settings

from .utils import get_document_properties, get_sorting_fields


class ESOrderingFilter:
    """
    A custom filter that is strongly inspired by the rest_framework ordering filter
    and has a similar interface.

    Note: in this filter ordering = None is the same as ordering = "__all__".
    """

    ordering_param = api_settings.ORDERING_PARAM
    ordering_fields = None

    def add_keyword_to_text_field_type(
        self, ordering: List[str], view: views.APIView
    ) -> List[str]:
        """
        Fields that have a 'text' field type are searchable on their keyword
        property.

        This adds .keyword to any field name that has a 'text' field type.
        """
        all_fields = self.get_all_fields(view)
        final_ordering = []
        for field_name in ordering:
            if field_name.startswith("-"):
                field_type = all_fields[field_name[1:]]
            else:
                field_type = all_fields[field_name]

            if field_type == field.Text.name:
                field_name = ".".join([field_name, field.Keyword.name])

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
            ordering = self.add_keyword_to_text_field_type(ordering, view)
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
        if properties:
            return {
                field_name: field_type
                for field_name, field_type in get_sorting_fields(properties)
            }

        return {}

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
