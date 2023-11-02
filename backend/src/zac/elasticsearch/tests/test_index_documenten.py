from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command

import requests_mock
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from freezegun import freeze_time
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
ZTC_ROOT = "https://api.ztc.nl/api/v1/"


@freeze_time("2020-01-01")
@requests_mock.Mocker()
class IndexDocumentsTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    iot = generate_oas_component(
        "ztc",
        "schemas/InformatieObjectType",
        url=f"{ZTC_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
        omschrijving="bijlage",
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
    )
    document = generate_oas_component(
        "drc",
        "schemas/EnkelvoudigInformatieObject",
        informatieobjecttype=iot["url"],
        url=f"{DRC_ROOT}enkelvoudiginformatieobjecten/8c21296c-af29-4f7a-86fd-02706a8187a0",
    )

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
        Service.objects.create(api_type=APITypes.ztc, api_root=ZTC_ROOT)

    def test_index_documenten_no_zaken_index(self, m):
        self.clear_index(init=False)
        with self.assertRaises(NotFoundError):
            call_command("index_documenten")

    def test_index_documenten(self, m):
        mock_service_oas_get(m, DRC_ROOT, "drc")
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        m.get(f"{ZTC_ROOT}informatieobjecttypen", json=paginated_response([self.iot]))
        m.get(
            f"{DRC_ROOT}enkelvoudiginformatieobjecten",
            json=paginated_response([self.document]),
        )
        m.get(f"{self.document['url']}/audittrail", status_code=404)

        index = Index(settings.ES_INDEX_DOCUMENTEN)
        self.refresh_index()
        self.assertEqual(index.search().count(), 0)
        call_command("index_documenten")
        self.refresh_index()
        self.assertEqual(index.search().count(), 1)

    def test_index_documenten_with_related_zaken(self, m):
        mock_service_oas_get(m, DRC_ROOT, "drc")
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        m.get(f"{ZTC_ROOT}informatieobjecttypen", json=paginated_response([self.iot]))
        m.get(
            f"{DRC_ROOT}enkelvoudiginformatieobjecten",
            json=paginated_response([self.document]),
        )
        m.get(f"{self.document['url']}/audittrail", status_code=404)

        index = Index(settings.ES_INDEX_DOCUMENTEN)
        zio = ZaakInformatieObjectDocument(
            url="https://some-url.com/", informatieobject=self.document["url"]
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
        with patch(
            "zac.elasticsearch.api.create_zaaktype_document", return_value=None
        ) as mock_create_ztd:
            call_command("index_documenten")
        mock_create_ztd.assert_called_once()
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
