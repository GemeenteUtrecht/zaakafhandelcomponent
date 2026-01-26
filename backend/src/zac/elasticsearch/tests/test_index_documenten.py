from django.conf import settings
from django.core.management import call_command

import requests_mock
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.core.models import CoreConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.mixins import FreezeTimeMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak, ZaakInformatieObject

from ..api import (
    create_zaak_document,
    create_zaakinformatieobject_document,
    create_zaaktype_document,
)
from ..documents import InformatieObjectDocument, ZaakInformatieObjectDocument
from ..searches import search_informatieobjects
from .utils import ESMixin

DRC_ROOT = "https://api.drc.nl/api/v1/"
ZTC_ROOT = "https://api.ztc.nl/api/v1/"
ZRC_ROOT = "https://api.zrc.nl/api/v1/"


@requests_mock.Mocker()
class IndexDocumentsTests(
    FreezeTimeMixin, ClearCachesMixin, ESMixin, APITransactionTestCase
):
    frozen_time = "2020-01-01"
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=f"{ZTC_ROOT}catalogussen/54fc5b67-f643-4da1-8c55-e5d75f17c56f",
    )
    iot = generate_oas_component(
        "ztc",
        "schemas/InformatieObjectType",
        url=f"{ZTC_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
        omschrijving="bijlage",
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        catalogus=catalogus["url"],
    )
    document1 = generate_oas_component(
        "drc",
        "schemas/EnkelvoudigInformatieObject",
        informatieobjecttype=iot["url"],
        url=f"{DRC_ROOT}enkelvoudiginformatieobjecten/8c21296c-af29-4f7a-86fd-02706a8187a0",
    )
    document2 = generate_oas_component(
        "drc",
        "schemas/EnkelvoudigInformatieObject",
        informatieobjecttype=iot["url"],
        url=f"{DRC_ROOT}enkelvoudiginformatieobjecten/8c21296c-af29-4f7a-86fd-02706a8187a1",
    )

    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_DOCUMENTEN).delete(ignore=404)
        Index(settings.ES_INDEX_ZIO).delete(ignore=404)

        if init:
            InformatieObjectDocument.init()
            ZaakInformatieObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_DOCUMENTEN).refresh()
        Index(settings.ES_INDEX_ZIO).refresh()

    def setUp(self):
        super().setUp()
        drc = ServiceFactory.create(api_type=APITypes.drc, api_root=DRC_ROOT)
        config = CoreConfig.get_solo()
        config.primary_drc = drc
        config.save()
        ServiceFactory.create(api_type=APITypes.ztc, api_root=ZTC_ROOT)

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
            json=paginated_response([self.document1]),
        )
        m.get(f"{self.document1['url']}/audittrail", status_code=404)

        index = Index(settings.ES_INDEX_DOCUMENTEN)
        self.refresh_index()
        self.assertEqual(index.search().count(), 0)
        call_command("index_documenten")
        self.refresh_index()
        self.assertEqual(index.search().count(), 1)

    def test_index_documenten_with_related_zaken(self, m):
        mock_service_oas_get(m, DRC_ROOT, "drc")
        mock_service_oas_get(m, ZTC_ROOT, "ztc")
        mock_service_oas_get(m, ZRC_ROOT, "zrc")

        index = Index(settings.ES_INDEX_DOCUMENTEN)
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{ZTC_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=self.catalogus["url"],
        )

        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZRC_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK1",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
        )
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZRC_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca9",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK2",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
        )
        zio1 = generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            url=f"{ZRC_ROOT}zaakinformatieobjecten/d859f08e-6957-44f8-9efb-502d18c28f8d",
            zaak=zaak1["url"],
            informatieobject=self.document1["url"],
        )
        zio2 = generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            url=f"{ZRC_ROOT}zaakinformatieobjecten/d859f08e-6957-44f8-9efb-502d18c28f8f",
            zaak=zaak1["url"],
            informatieobject=self.document2["url"],
        )
        zio3 = generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            url=f"{ZRC_ROOT}zaakinformatieobjecten/d859f08e-6957-44f8-9efb-502d18c28f8e",
            zaak=zaak2["url"],
            informatieobject=self.document1["url"],
        )

        m.get(f"{ZTC_ROOT}informatieobjecttypen", json=paginated_response([self.iot]))
        m.get(
            f"{DRC_ROOT}enkelvoudiginformatieobjecten",
            json=paginated_response([self.document1, self.document2]),
        )
        mock_resource_get(m, self.document1)
        mock_resource_get(m, self.document2)
        m.get(f"{self.document1['url']}/audittrail", status_code=404)
        m.get(f"{self.document2['url']}/audittrail", status_code=404)
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, zaaktype)

        zt_obj = factory(ZaakType, zaaktype)
        zaak1_obj = factory(Zaak, zaak1)
        zaak1_obj.zaaktype = zt_obj
        zaak2_obj = factory(Zaak, zaak2)
        zaak2_obj.zaaktype = zt_obj
        zt_doc = create_zaaktype_document(zt_obj)
        zaak1_doc = create_zaak_document(zaak1_obj)
        zaak1_doc.zaaktype = zt_doc
        ziod1 = create_zaakinformatieobject_document(
            factory(ZaakInformatieObject, zio1)
        )
        ziod1.save()
        ziod2 = create_zaakinformatieobject_document(
            factory(ZaakInformatieObject, zio2)
        )
        ziod2.save()

        zaak2_doc = create_zaak_document(zaak2_obj)
        zaak2_doc.zaaktype = zt_doc
        ziod3 = create_zaakinformatieobject_document(
            factory(ZaakInformatieObject, zio3)
        )
        ziod3.save()

        zaak1_doc.save()
        zaak2_doc.save()
        self.refresh_index()

        self.assertEqual(index.search().count(), 0)
        call_command("index_documenten")

        self.refresh_index()

        self.assertEqual(index.search().count(), 2)
        results = search_informatieobjects(zaak=zaak1_obj.url)
        self.assertEqual(len(results), 2)

        results = search_informatieobjects(zaak=zaak2_obj.url)
        self.assertEqual(len(results), 1)
