from django.conf import settings
from django.test import TestCase

from elasticsearch_dsl import Document, InnerDoc, field
from rest_framework import views
from rest_framework.test import APIRequestFactory

from ..drf_api.filters import ESOrderingFilter


class NestedEsTestDocument(InnerDoc):
    some_nested_text = field.Text(fields={"keyword": field.Keyword()})


class ESTestDocument(Document):
    some_nested = field.Nested(NestedEsTestDocument)
    some_date = field.Date()
    some_sortable_text = field.Text(fields={"keyword": field.Keyword()})
    some_text = field.Text()
    some_keyword = field.Keyword()
    some_boolean = field.Boolean()
    some_object = field.Object()

    class Index:
        name = settings.ES_INDEX_ZAKEN


class ESOrderingFilterTest(TestCase):
    def test_view_default_ordering(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(f"/some-url", {}, format="json")

        class SomeView(views.APIView):
            ordering = ("some_date",)

        some_request = SomeView().initialize_request(some_request)
        ordering = ESOrderingFilter().get_ordering(some_request, SomeView)
        self.assertEqual(ordering, ("some_date",))

    def test_view_without_search_document(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(
            f"/some-url?ordering=some_text", {}, format="json"
        )

        class SomeView(views.APIView):
            pass

        with self.assertRaises(AttributeError):
            ESOrderingFilter().get_ordering(some_request, SomeView)

    def test_view_with_search_document_with_keyword_text_field(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(
            f"/some-url?ordering=some_sortable_text", {}, format="json"
        )

        class SomeView(views.APIView):
            search_document = ESTestDocument

        some_request = SomeView().initialize_request(some_request)
        ordering = ESOrderingFilter().get_ordering(some_request, SomeView)
        self.assertEqual(ordering, ["some_sortable_text.keyword"])

    def test_view_with_search_document_no_keyword_text_field(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(
            f"/some-url?ordering=some_text", {}, format="json"
        )

        class SomeView(views.APIView):
            search_document = ESTestDocument

        some_request = SomeView().initialize_request(some_request)
        ordering = ESOrderingFilter().get_ordering(some_request, SomeView)
        self.assertEqual(ordering, None)

    def test_remove_invalid_fields(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(
            f"/some-url?ordering=some_date,something_that_doesntexist",
            {},
            format="json",
        )

        class SomeView(views.APIView):
            search_document = ESTestDocument

        some_request = SomeView().initialize_request(some_request)
        ordering = ESOrderingFilter().get_ordering(some_request, SomeView)
        self.assertEqual(ordering, ["some_date"])

    def test_reversed_fields(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(
            f"/some-url?ordering=-some_sortable_text", {}, format="json"
        )

        class SomeView(views.APIView):
            search_document = ESTestDocument

        some_request = SomeView().initialize_request(some_request)
        ordering = ESOrderingFilter().get_ordering(some_request, SomeView)
        self.assertEqual(ordering, ["-some_sortable_text.keyword"])

    def test_multiple_fields(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(
            f"/some-url?ordering=-some_date,some_boolean", {}, format="json"
        )

        class SomeView(views.APIView):
            search_document = ESTestDocument

        some_request = SomeView().initialize_request(some_request)
        ordering = ESOrderingFilter().get_ordering(some_request, SomeView)
        self.assertEqual(ordering, ["-some_date", "some_boolean"])

    def test_nested_fields(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(
            f"/some-url?ordering=some_nested.some_nested_text", {}, format="json"
        )

        class SomeView(views.APIView):
            search_document = ESTestDocument

        some_request = SomeView().initialize_request(some_request)
        ordering = ESOrderingFilter().get_ordering(some_request, SomeView)
        self.assertEqual(ordering, ["some_nested.some_nested_text.keyword"])

    def test_set_ordering_fields(self):
        request_factory = APIRequestFactory()
        some_request = request_factory.post(
            f"/some-url?ordering=some_boolean,some_date", {}, format="json"
        )

        class SomeView(views.APIView):
            search_document = ESTestDocument
            ordering_fields = (
                "some_date",
                "some_keyword",
            )

        some_request = SomeView().initialize_request(some_request)
        ordering = ESOrderingFilter().get_ordering(some_request, SomeView)
        self.assertEqual(ordering, ["some_date"])
