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

    def has_access(self, obj):
        raise NotImplementedError("This method must be implemented by a subclass")

    def search_query(self) -> Query:
        raise NotImplementedError("This method must be implemented by a subclass")

    def short_display(self) -> str:
        return "-"


@dataclass(frozen=True)
class Permission:
    name: str
    description: str
    blueprint_class: Optional[Type[Blueprint]] = None

    def __post_init__(self):
        if self.name in registry:
            raise ImproperlyConfigured(
                "Permission with name '%s' already exists" % self.name
            )
        registry[self.name] = self

    def __hash__(self):
        return hash(self.name)
