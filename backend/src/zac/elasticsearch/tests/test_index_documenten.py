from django.conf import settings
from django.core.management import call_command

import requests_mock
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.datastructures import VA_ORDER
from zac.core.models import CoreConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response

from ..documents import (
    InformatieObjectDocument,
    ZaakDocument,
    ZaakInformatieObjectDocument,
)
from .utils import ESMixin

DRC_ROOT = "https://api.drc.nl/api/v1/"


@requests_mock.Mocker()
class IndexDocumentsTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_DOCUMENTEN).delete(ignore=404)

        if init:
            InformatieObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_DOCUMENTEN).refresh()

    def setUp(self):
        super().setUp()
        drc = Service.objects.create(api_type=APITypes.drc, api_root=DRC_ROOT)
        config = CoreConfig.get_solo()
        config.primary_drc = drc
        config.save()

    def test_index_documenten_no_zaken_index(self, m):
        self.clear_index(init=False)
        with self.assertRaises(NotFoundError):
            call_command("index_documenten")

    def test_index_documenten(self, m):
        mock_service_oas_get(m, DRC_ROOT, "drc")
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )

        m.get(
            f"{DRC_ROOT}enkelvoudiginformatieobjecten",
            json=paginated_response([document]),
        )
        index = Index(settings.ES_INDEX_DOCUMENTEN)
        self.refresh_index()
        self.assertEqual(index.search().count(), 0)
        call_command("index_documenten")
        self.refresh_index()
        self.assertEqual(index.search().count(), 1)

    def test_index_documenten_with_related_zaken(self, m):
        mock_service_oas_get(m, DRC_ROOT, "drc")
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )

        m.get(
            f"{DRC_ROOT}enkelvoudiginformatieobjecten",
            json=paginated_response([document]),
        )
        index = Index(settings.ES_INDEX_DOCUMENTEN)
        zio = ZaakInformatieObjectDocument(
            url="https://some-url.com/", informatieobject=document["url"]
        )
        zd = ZaakDocument(
            identificatie="some-identificatie",
            omschrijving="some-omschrijving",
            bronorganisatie="some-bronorganisatie",
            zaakinformatieobjecten=[zio],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            va_order=VA_ORDER[VertrouwelijkheidsAanduidingen.openbaar],
        )
        zd.save()
        self.refresh_index()
        self.assertEqual(index.search().count(), 0)
        call_command("index_documenten")
        self.refresh_index()
        self.assertEqual(index.search().count(), 1)
        self.assertEqual(
            index.search().execute()[0].related_zaken,
            [
                {
                    "bronorganisatie": "some-bronorganisatie",
                    "omschrijving": "some-omschrijving",
                    "identificatie": "some-identificatie",
                    "va_order": 27,
                }
            ],
        )
