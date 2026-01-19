from django.conf import settings
from django.test import TestCase

from drf_spectacular.openapi import OpenApiParameter
from elasticsearch_dsl import Document, InnerDoc, field

from ..drf_api.utils import (
    es_document_to_ordering_parameters,
    get_document_fields,
    get_document_properties,
)


class NestedEsTestDocument(InnerDoc):
    some_nested_text = field.Text(fields={"keyword": field.Keyword()})


class ESTestDocument(Document):
    some_nested = field.Nested(NestedEsTestDocument)
    some_date = field.Date()
    some_text = field.Text()
    some_keyword = field.Keyword()
    some_boolean = field.Boolean()
    some_object = field.Object()

    class Index:
        name = settings.ES_INDEX_ZAKEN


class UtilsTests(TestCase):
    def test_get_document_properties(self):
        properties = get_document_properties(ESTestDocument)
        expected_data = {
            "properties": {
                "some_nested": {
                    "properties": {
                        "some_nested_text": {
                            "fields": {"keyword": {"type": "keyword"}},
                            "type": "text",
                        }
                    },
                    "type": "nested",
                },
                "some_date": {"type": "date"},
                "some_text": {"type": "text"},
                "some_keyword": {"type": "keyword"},
                "some_boolean": {"type": "boolean"},
                "some_object": {"type": "object"},
            }
        }
        self.assertEqual(properties, expected_data)

    def test_get_document_properties_fail(self):
        class NotAnESDocument:
            mooi = "mooi"

        with self.assertRaises(AssertionError):
            get_document_properties(NotAnESDocument)

    def test_get_document_fields(self):
        properties = get_document_properties(ESTestDocument)
        list_of_fields = list(
            get_document_fields(properties["properties"], sortable=True)
        )
        expected_data = [
            ("some_nested.some_nested_text", "text"),
            ("some_date", "date"),
            ("some_keyword", "keyword"),
            ("some_boolean", "boolean"),
        ]
        self.assertCountEqual(list_of_fields, expected_data)

        properties = get_document_properties(ESTestDocument)
        list_of_fields = list(
            get_document_fields(properties["properties"], sortable=False)
        )
        expected_data = [
            ("some_nested.some_nested_text", "text"),
            ("some_date", "date"),
            ("some_text", "text"),
            ("some_keyword", "keyword"),
            ("some_boolean", "boolean"),
        ]
        self.assertCountEqual(list_of_fields, expected_data)

    def test_es_document_to_ordering_parameters(self):
        parameter = es_document_to_ordering_parameters(ESTestDocument)
        self.assertTrue(isinstance(parameter, OpenApiParameter))
        expected_data = [
            "some_nested.some_nested_text",
            "some_date",
            "some_keyword",
            "some_boolean",
        ]
        self.assertCountEqual(parameter.enum, expected_data)
