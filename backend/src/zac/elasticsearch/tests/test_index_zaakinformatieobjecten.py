from io import StringIO

from django.conf import settings
from django.core.management import call_command

import requests_mock
from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.constants import APITypes

from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from ..api import create_zaak_document
from ..documents import ZaakInformatieObjectDocument
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"
DRC_ROOT = "https://api.drc.nl/api/v1/"


@requests_mock.Mocker()
class IndexZaakInformatieObjectenTests(
    ClearCachesMixin, ESMixin, APITransactionTestCase
):
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        catalogus=catalogus["url"],
    )
    zaak = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        zaaktype=zaaktype["url"],
        bronorganisatie="002220647",
        identificatie="ZAAK-001",
        vertrouwelijkheidaanduiding="zaakvertrouwelijk",
    )
    zaakinformatieobject = generate_oas_component(
        "zrc",
        "schemas/ZaakInformatieObject",
        url=f"{ZAKEN_ROOT}zaakinformatieobjecten/f79989d3-9ac4-4c2b-a94e-13191b333444",
        zaak=zaak["url"],
        informatieobject=f"{DRC_ROOT}enkelvoudiginformatieobjecten/d859f08e-6957-44f8-9efb-502d18c28f8f",
    )

    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_ZIO).delete(ignore=404)

        if init:
            ZaakInformatieObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_ZIO).refresh()

    def setUp(self):
        super().setUp()
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def test_index_zio(self, m):
        # mock API requests
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json=paginated_response([self.zaak]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}",
            json=[self.zaakinformatieobject],
        )

        call_command("index_zaakinformatieobjecten", stdout=StringIO())
        self.refresh_index()

        # check zio_document exists
        zio_document = ZaakInformatieObjectDocument.get(
            id=self.zaakinformatieobject["url"].split("/")[-1]
        )
        self.assertEqual(zio_document.zaak, self.zaakinformatieobject["zaak"])
        self.assertEqual(
            zio_document.informatieobject, self.zaakinformatieobject["informatieobject"]
        )
        self.assertEqual(zio_document.url, self.zaakinformatieobject["url"])

    def test_index_zio_reindex_last_argument(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json=paginated_response([self.zaak]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}",
            json=[self.zaakinformatieobject],
        )

        call_command("index_zaakinformatieobjecten", stdout=StringIO())
        self.refresh_index()

        # check zaak_document exists
        zio_document = ZaakInformatieObjectDocument.get(
            id=self.zaakinformatieobject["url"].split("/")[-1]
        )
        self.assertEqual(zio_document.zaak, self.zaakinformatieobject["zaak"])
        self.assertEqual(
            zio_document.informatieobject, self.zaakinformatieobject["informatieobject"]
        )
        self.assertEqual(zio_document.url, self.zaakinformatieobject["url"])

        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca9",
            zaaktype=self.zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK-002",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            status=None,
        )
        zaakinformatieobject2 = generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            url=f"{ZAKEN_ROOT}zaakinformatieobjecten/f79989d3-9ac4-4c2b-a94e-13191b333444",
            zaak=zaak2["url"],
            informatieobject=f"{DRC_ROOT}enkelvoudiginformatieobjecten/d859f08e-6957-44f8-9efb-502d18c28f8f",
        )
        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([zaak2, self.zaak]))
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak2['url']}",
            json=[zaakinformatieobject2],
        )

        zaak = factory(Zaak, self.zaak)
        zaak.zaaktype = factory(ZaakType, self.zaaktype)
        zaak2 = factory(Zaak, zaak2)
        zaak2.zaaktype = factory(ZaakType, self.zaaktype)
        zd2 = create_zaak_document(zaak2)
        zd2.save()
        zd = create_zaak_document(zaak)
        zd.save()
        self.refresh_index()

        call_command("index_zaakinformatieobjecten", reindex_last=1)
        self.refresh_index()
        # check zaak_document exists
        zio_document = ZaakInformatieObjectDocument.get(
            id=zaakinformatieobject2["url"].split("/")[-1]
        )
        self.assertEqual(zio_document.zaak, zaakinformatieobject2["zaak"])
        self.assertEqual(
            zio_document.informatieobject, zaakinformatieobject2["informatieobject"]
        )
        self.assertEqual(zio_document.url, zaakinformatieobject2["url"])
