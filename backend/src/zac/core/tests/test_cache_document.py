from unittest.mock import MagicMock, patch

from django.core.cache import cache

import requests_mock
from rest_framework.test import APITransactionTestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.core.cache import invalidate_document_cache
from zac.core.services import _fetch_document, find_document, get_document
from zac.core.tests.utils import ClearCachesMixin

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"


@requests_mock.Mocker()
class TestCacheDocuments(ClearCachesMixin, APITransactionTestCase):
    def test_fetch_document_sets_cache(self, m):
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        document_url = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6"
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=document_url,
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            versie="110",
        )
        m.get(document_url, json=document)

        # Assert documents aren't cached already
        self.assertFalse(cache.get(f"document:{document_url}"))
        self.assertFalse(
            cache.get(
                f"document:{document['bronorganisatie']}:{document['identificatie']}:None"
            )
        )

        # Call _fetch_document which will check cache and set cache is necessary
        _fetch_document(document_url)

        # Assert documents are now cached
        self.assertTrue(cache.get(f"document:{document_url}"))
        self.assertTrue(
            cache.get(
                f"document:{document['bronorganisatie']}:{document['identificatie']}:None"
            )
        )

    @patch("zac.core.services.cache")
    def test_fetch_document_cached(self, m, mock_cache):
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        document_url = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6"
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=document_url,
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            versie="110",
        )
        m.get(document_url, json=document)
        _fetch_document(document_url)

        mock_cache.__contains__ = lambda *args: True
        mock_cache.get = MagicMock()
        mock_cache.get.return_value = document
        # See if cache is used in a second call
        _fetch_document(document_url)

        self.assertEqual(mock_cache.get.call_count, 1)
        mock_cache.get.assert_called_with(f"document:{document_url}")

    @patch("zac.core.services.cache")
    def test_find_document_cached(self, m, mock_cache):
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        document_url = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6"
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=document_url,
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            versie=110,
        )
        m.get(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten?bronorganisatie=123456782&identificatie=DOC-2020-007",
            json={"results": [document], "next": None},
        )

        mock_cache.get = MagicMock()
        mock_cache.get.return_value = None
        find_document("123456782", "DOC-2020-007", versie=110)
        result = MagicMock()
        result.json.return_value = document
        mock_cache.get.return_value = result

        # See if cache is used in a second call
        find_document("123456782", "DOC-2020-007", versie=110)

        self.assertEqual(mock_cache.get.call_count, 2)
        mock_cache.get.assert_called_with(
            f"document:{document['bronorganisatie']}:{document['identificatie']}:{document['versie']}"
        )

    def test_no_cache_document_404(self, m):
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document_url = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6"
        m.get(document_url, json={"some-error": None}, status_code=404)

        # Cache is empty
        self.assertFalse(cache.get(f"document:{document_url}"))

        response = _fetch_document(document_url)
        self.assertEqual(response.json(), {"some-error": None})
        self.assertEqual(response.status_code, 404)

        # Nothing got cached
        self.assertFalse(cache.get(f"document:{document_url}"))

    def test_invalidate_cache(self, m):
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        document_url = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6"
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=document_url,
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            versie="110",
        )
        m.get(document_url, json=document)

        # Cache is empty
        self.assertFalse(cache.get(f"document:{document_url}"))
        self.assertFalse(
            cache.get(
                f"document:{document['bronorganisatie']}:{document['identificatie']}:None"
            )
        )

        document = get_document(document_url)

        # Assert documents are now cached
        self.assertTrue(cache.get(f"document:{document_url}"))
        self.assertTrue(
            cache.get(
                f"document:{document.bronorganisatie}:{document.identificatie}:None"
            )
        )

        # Clear cache for document
        invalidate_document_cache(document)

        # Cache got cleared
        self.assertFalse(cache.get(f"document:{document_url}"))
        self.assertFalse(
            cache.get(
                f"document:{document.bronorganisatie}:{document.identificatie}:None"
            )
        )
