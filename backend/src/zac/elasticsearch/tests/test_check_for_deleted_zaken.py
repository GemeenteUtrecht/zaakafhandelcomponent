from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command

import requests_mock
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.constants import APITypes

from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

from ..documents import ZaakDocument
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"


@requests_mock.Mocker()
class IndexZakenTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    def setUp(self):
        super().setUp()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def test_check_for_deleted_zaken_fail_no_index(self, m):
        # Make sure no index exists
        self.clear_index()

        with self.assertRaises(NotFoundError):
            call_command("check_for_deleted_zaken", stdout=StringIO())

    def test_check_for_deleted_zaken(self, m):
        self.clear_index()

        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=CATALOGUS_URL,
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK1",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            eigenschappen=[],
        )
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/b321d30c-6c10-47fe-82e3-e9f524c14ca9",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK2",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            eigenschappen=[],
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zaaktype],
            },
        )
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json={"count": 2, "previous": None, "next": None, "results": [zaak, zaak2]},
        )
        m.get(
            f"{ZAKEN_ROOT}rollen",
            json={"count": 0, "previous": None, "next": None, "results": []},
        )
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak['url']}", json=paginated_response([])
        )
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak2['url']}", json=paginated_response([])
        )
        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak['url']}", json=[])
        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak2['url']}", json=[])
        mock_resource_get(m, zaaktype)
        mock_resource_get(m, catalogus)
        with patch(
            "zac.elasticsearch.management.commands.index_zaken.get_zaakeigenschappen",
            return_value=[],
        ):
            call_command("index_zaken", stdout=StringIO())
        self.refresh_index()
        zaken = Index(settings.ES_INDEX_ZAKEN)
        self.assertEqual(zaken.search().count(), 2)

        # check zaak_documenten exist
        zaak_document1 = ZaakDocument.get(id="a522d30c-6c10-47fe-82e3-e9f524c14ca8")
        zaak_document2 = ZaakDocument.get(id="b321d30c-6c10-47fe-82e3-e9f524c14ca9")

        self.assertEqual(zaak_document1.identificatie, "ZAAK1")
        self.assertEqual(zaak_document2.identificatie, "ZAAK2")

        # mock the deletion of a zaak
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json={"count": 1, "previous": None, "next": None, "results": [zaak]},
        )
        call_command("check_for_deleted_zaken", stdout=StringIO())
        self.refresh_index()
        self.assertEqual(zaken.search().count(), 1)

        # Make sure only ZAAK1 exists
        zaak_document1 = ZaakDocument.get(id="a522d30c-6c10-47fe-82e3-e9f524c14ca8")
        self.assertEqual(zaak_document1.identificatie, "ZAAK1")

        with self.assertRaises(NotFoundError):
            zaak_document2 = ZaakDocument.get(id="b321d30c-6c10-47fe-82e3-e9f524c14ca9")
