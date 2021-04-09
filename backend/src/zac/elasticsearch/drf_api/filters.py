from typing import List, Tuple

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from drf_spectacular.plumbing import force_instance
from rest_framework import serializers, views
from rest_framework.settings import api_settings

from zac.api.drf_spectacular.utils import get_sorting_fields


class ESOrderingFilter:
    ordering_param = api_settings.ORDERING_PARAM
    ordering_fields = None

    def get_ordering(self, request, view):
        """
        Ordering is set by a comma delimited ?ordering=... query parameter.

        The `ordering` query parameter can be overridden by setting
        the `ordering_param` value on the OrderingFilter or by
        specifying an `ORDERING_PARAM` value in the API settings.
        """
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(",")]
            ordering = self.remove_invalid_fields(fields, view, request)
            if ordering:
                return ordering

        return self.get_default_ordering(view)

    def get_default_ordering(self, view):
        ordering = getattr(view, "ordering", None)
        if isinstance(ordering, str):
            return (ordering,)
        return ordering

    def get_default_valid_fields(self, view, context={}):
        # If `ordering_fields` is not specified, then we determine a default
        # based on the serializer class, if one exists on the view.
        if hasattr(view, "get_serializer_class"):
            try:
                serializer_class = view.get_serializer_class()
            except AssertionError:
                # Raised by the default implementation if
                # no serializer_class was found
                serializer_class = None
        else:
            serializer_class = getattr(view, "serializer_class", None)

        if serializer_class is None:
            msg = (
                "Cannot use %s on a view which does not have either a "
                "'serializer_class', an overriding 'get_serializer_class' "
                "or 'ordering_fields' attribute."
            )
            raise ImproperlyConfigured(msg % self.__class__.__name__)

        return [
            (field.source.replace(".", "__") or field_name, field.label)
            for field_name, field in serializer_class(context=context).fields.items()
            if not getattr(field, "write_only", False) and not field.source == "*"
        ]

    def get_results_serializer(self, view: views.APIView) -> serializers.Serializer:
        assert hasattr(
            view, "results_serializer_class"
        ), f"{self.__class__.__name__} requires results_serializer_class to be set on view."
        serializer = force_instance(view.results_serializer_class)
        return serializer

    def get_valid_fields(self, view, context={}) -> List[Tuple[str, str]]:
        ordering_fields = getattr(view, "ordering_fields", self.ordering_fields)

        if ordering_fields is None:
            # Default to allowing filtering on serializer fields
            return self.get_default_valid_fields(view, context)

        serializer = self.get_results_serializer(view)
        all_valid_fields = get_sorting_fields(serializer.fields)
        if ordering_fields == "__all__":
            return [(field, field) for field in all_valid_fields]

        else:
            valid_fields = []
            for field in ordering_fields:
                if not isinstance(field, str):
                    field = field[0]

                if field in all_valid_fields:
                    valid_fields.append((field, field))

        return valid_fields

    def remove_invalid_fields(self, fields, view, request):
        valid_fields = [
            item[0] for item in self.get_valid_fields(view, {"request": request})
        ]

        def term_valid(term):
            if term.startswith("-"):
                term = term[1:]
            return term in valid_fields

        return [term for term in fields if term_valid(term)]
