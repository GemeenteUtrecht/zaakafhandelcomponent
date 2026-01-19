from unittest.mock import MagicMock, patch

from django.core.cache import cache

import requests_mock
from requests import Response
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes

from zac.core.cache import (
    invalidate_document_other_cache,
    invalidate_document_url_cache,
)
from zac.core.services import _fetch_document, find_document, get_document
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
DOCUMENT_URL = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6"


@requests_mock.Mocker()
class TestCacheDocuments(ClearCachesMixin, APITransactionTestCase):
    document = generate_oas_component(
        "drc",
        "schemas/EnkelvoudigInformatieObject",
        url=DOCUMENT_URL,
        identificatie="DOC-2020-007",
        bronorganisatie="123456782",
        versie="110",
    )

    def test_fetch_document_sets_cache(self, m):
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        mock_resource_get(m, self.document)

        # Assert documents aren't cached already
        self.assertFalse(cache.get(f"document:{DOCUMENT_URL}"))
        self.assertFalse(
            cache.get(
                f"document:{self.document['bronorganisatie']}:{self.document['identificatie']}:None"
            )
        )

        # Call _fetch_document which will check cache and set cache is necessary
        _fetch_document(DOCUMENT_URL)

        # Assert documents are now cached
        self.assertTrue(cache.get(f"document:{DOCUMENT_URL}"))
        self.assertTrue(
            cache.get(
                f"document:{self.document['bronorganisatie']}:{self.document['identificatie']}:None"
            )
        )

        # Assert cache.get(f"document:{document['bronorganisatie']}:{document['identificatie']}:{versie}")
        # returns a Document type ...
        document = cache.get(
            f"document:{self.document['bronorganisatie']}:{self.document['identificatie']}:None"
        )
        self.assertTrue(isinstance(document, Document))
        # ... and cache.get(f"document:{document_url}") returns a Response type.
        response = cache.get(f"document:{DOCUMENT_URL}")
        self.assertTrue(isinstance(response, Response))

    def test_invalidate_cache(self, m):
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        mock_resource_get(m, self.document)

        # Cache is empty
        self.assertFalse(cache.get(f"document:{DOCUMENT_URL}"))
        self.assertFalse(
            cache.get(
                f"document:{self.document['bronorganisatie']}:{self.document['identificatie']}:None"
            )
        )

        document = get_document(DOCUMENT_URL)

        # Assert documents are now cached
        self.assertTrue(cache.get(f"document:{DOCUMENT_URL}"))
        self.assertTrue(
            cache.get(
                f"document:{self.document['bronorganisatie']}:{self.document['identificatie']}:None"
            )
        )

        # Clear cache for document
        invalidate_document_url_cache(document.url)
        invalidate_document_other_cache(document)

        # Cache got cleared
        self.assertFalse(cache.get(f"document:{DOCUMENT_URL}"))
        self.assertFalse(
            cache.get(
                f"document:{self.document['bronorganisatie']}:{self.document['identificatie']}:None"
            )
        )

    @patch("zac.core.services.cache")
    def test_fetch_document_cached(self, m, mock_cache):
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        mock_resource_get(m, self.document)
        _fetch_document(DOCUMENT_URL)

        mock_cache.__contains__ = lambda *args: True
        mock_cache.get = MagicMock()
        mock_cache.get.return_value = self.document
        # See if cache is used in a second call
        _fetch_document(DOCUMENT_URL)

        self.assertEqual(mock_cache.get.call_count, 1)
        mock_cache.get.assert_called_with(f"document:{DOCUMENT_URL}")

    def test_find_document_cached_latest_version(self, m):
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        m.get(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten?bronorganisatie=123456782&identificatie=DOC-2020-007",
            json={"results": [self.document], "next": None},
        )

        # Assert document isn't already in cache
        self.assertFalse(f"document:123456782:DOC-2020-007:None" in cache)
        with patch("zac.core.services.search_informatieobjects", return_value=None):
            find_document("123456782", "DOC-2020-007")
        # Assert document is now cached
        self.assertTrue(f"document:123456782:DOC-2020-007:None" in cache)

        # See if cache is used in a second call - change response on getting paginated results in find_document function
        document_2 = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=DOCUMENT_URL,
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            versie=110,
            inhoud="http://www.some-other-content.com/",
        )
        m.get(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten?bronorganisatie=123456782&identificatie=DOC-2020-007",
            json={"results": [document_2], "next": None},
        )
        with patch("zac.core.services.search_informatieobjects", return_value=None):
            result = find_document("123456782", "DOC-2020-007")

        # If result.inhoud is the same inhoud as document['inhoud']
        # and NOT document_2['inhoud'] cache was called and not the function body.
        # This scenario won't happen in practice because any
        # update to drc document will bump the version, just for testing purposes.
        self.assertEqual(result.inhoud, self.document["inhoud"])

        # Clear cache and see if we get the latest inhoud
        invalidate_document_url_cache(self.document["url"])
        invalidate_document_other_cache(factory(Document, self.document))
        with patch("zac.core.services.search_informatieobjects", return_value=None):
            result = find_document("123456782", "DOC-2020-007")
        self.assertEqual(result.inhoud, document_2["inhoud"])

    def test_find_document_cached_without_candidate(self, m):
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")

        # Return "results" but without the specified version so that candidates will be an empty list.
        m.get(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten?bronorganisatie=123456782&identificatie=DOC-2020-007",
            json={"results": [self.document], "next": None},
        )

        # Mock the right version so that _fetch_document will find it.
        document_2 = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=DOCUMENT_URL,
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            versie=100,
        )
        m.get(f"{DOCUMENT_URL}?versie=100", json=document_2)

        # Assert both documents arent already cached
        self.assertFalse(f"document:123456782:DOC-2020-007:100" in cache)
        self.assertFalse(f"document:123456782:DOC-2020-007:110" in cache)
        self.assertFalse(f"document:{DOCUMENT_URL}" in cache)
        self.assertFalse(f"document:{DOCUMENT_URL}?versie=100" in cache)
        with patch("zac.core.services.search_informatieobjects", return_value=None):
            find_document("123456782", "DOC-2020-007", versie=100)

        # Assert document with version 110 is now cached
        self.assertTrue(f"document:123456782:DOC-2020-007:100" in cache)
        self.assertTrue(f"document:{DOCUMENT_URL}?versie=100" in cache)

    def test_no_cache_document_404(self, m):
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        m.get(DOCUMENT_URL, json={"some-error": None}, status_code=404)

        # Cache is empty
        self.assertFalse(cache.get(f"document:{DOCUMENT_URL}"))

        response = _fetch_document(DOCUMENT_URL)
        self.assertEqual(response.json(), {"some-error": None})
        self.assertEqual(response.status_code, 404)

        # Nothing got cached
        self.assertFalse(cache.get(f"document:{DOCUMENT_URL}"))
