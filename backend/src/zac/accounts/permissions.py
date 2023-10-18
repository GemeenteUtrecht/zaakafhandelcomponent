from dataclasses import dataclass
from typing import Optional, Type

from django.core.exceptions import ImproperlyConfigured
from django.utils.html import format_html

import yaml
from drf_spectacular.openapi import AutoSchema
from elasticsearch_dsl.query import Query
from rest_framework.serializers import Serializer

from drf_jsonschema import to_jsonschema

registry = {}
object_type_registry = {}


class Blueprint(Serializer):
    """
    class to validate and manage blueprint permissions
    """

    @classmethod
    def display_as_yaml(cls):
        auto_schema = AutoSchema()
        auto_schema.method = "GET"
        schema = auto_schema._map_serializer(cls, "")
        schema_yaml = yaml.dump(schema)
        return format_html("<pre>{}</pre>", schema_yaml)

    @classmethod
    def display_as_jsonschema(cls):
        json_schema = to_jsonschema(cls())
        return json_schema

    def has_access(self, obj, permission=None):
        raise NotImplementedError("This method must be implemented by a subclass")

    def search_query(self, on_nested_field: Optional[str] = "") -> Query:
        raise NotImplementedError("This method must be implemented by a subclass")

    def short_display(self) -> str:
        return "-"


@dataclass(frozen=True)
class PermissionObjectType:
    name: str
    blueprint_class: Optional[Type[Blueprint]] = None

    def __post_init__(self):
        if self.name in object_type_registry:
            raise ImproperlyConfigured(
                "Object type with name '%s' already exists" % self.name
            )
        object_type_registry[self.name] = self


@dataclass(frozen=True)
class Permission:
    """
    Base dataclass defining a Permission.
    """

    name: str
    description: str

    def __post_init__(self):
        if self.name in registry:
            raise ImproperlyConfigured(
                "Permission with name '%s' already exists" % self.name
            )
        registry[self.name] = self

    def __hash__(self):
        return hash(self.name)
