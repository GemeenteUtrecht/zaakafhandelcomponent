import copy
from collections import OrderedDict

from django_filters.rest_framework.backends import DjangoFilterBackend
from rest_framework import fields
from rest_framework.serializers import Serializer


class ApiFilterBackend(DjangoFilterBackend):
    def get_filterset_class(self, view, queryset=None):
        return getattr(view, "filterset_class", None)


class ApiFilterSetMetaclass(type):
    def __new__(cls, name, bases, attrs):
        attrs["_filters"] = cls.get_filters(bases, attrs)

        return super().__new__(cls, name, bases, attrs)

    @classmethod
    def get_filters(cls, bases, attrs):
        filters = [
            (filter_name, attrs.pop(filter_name))
            for filter_name, obj in list(attrs.items())
            if isinstance(obj, fields.Field)
        ]
        filters.sort(key=lambda x: x[1]._creation_counter)

        return OrderedDict(filters)


class BaseApiFilterSet:
    def __init__(self, data=None, queryset=None, *, request=None):
        self.data = data or {}
        self.queryset = queryset
        self.request = request
        self.is_bound = data is not None
        self.filters = copy.deepcopy(self._filters)

    def get_serializer_class(self):
        return type(
            str("%sSerializer" % self.__class__.__name__), (Serializer,), self.filters
        )

    @property
    def serializer(self):
        if not hasattr(self, "_serializer"):
            Serializer = self.get_serializer_class()
            if self.is_bound:
                self._serializer = Serializer(data=self.data)
            else:
                self._serializer = Serializer()
        return self._serializer

    def is_valid(self):
        """
        Return True if the underlying serializer has no errors, or False otherwise.
        """
        return self.is_bound and self.serializer.is_valid()

    @property
    def errors(self):
        """
        Return an ErrorDict for the data provided for the underlying form.
        """
        return self.serializer.errors

    @property
    def qs(self):
        if not hasattr(self, "_qs"):
            qs = self.queryset
            if self.is_bound:
                # ensure form validation before filtering
                self.errors
                qs = self.filter_queryset(qs)
            self._qs = qs
        return self._qs

    def filter_queryset(self, queryset: list):
        """
        Filter queryset using filter_<filter_name> methods of the filterset
        """
        for name, value in self.serializer.data.items():
            method_name = f"filter_{name}"
            if not hasattr(self, method_name):
                raise NotImplemented(
                    "%s method should be implemented in the filterset" % method_name
                )
            method = getattr(self, method_name)
            queryset = method(queryset, value)
        return queryset


class ApiFilterSet(BaseApiFilterSet, metaclass=ApiFilterSetMetaclass):
    """
    This class can be used for API Views where a model is not defined
    Only declared filters are supported:
    * they should be subclasses of rest_framework.fields.Field class
    * for each filter 'filter_<name>' method of the FilterSet should be defined
    """

    pass
