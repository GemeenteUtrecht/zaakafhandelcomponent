from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command

import requests_mock
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.datastructures import VA_ORDER
from zac.core.models import CoreConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response

from ..documents import ObjectDocument, ZaakDocument, ZaakObjectDocument
from .utils import ESMixin

OBJECTS_ROOT = "https://api.objects.nl/api/v1/"
OBJECTTYPES_ROOT = "https://api.objecttypes.nl/api/v2/"


@requests_mock.Mocker()
class IndexObjectsTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_OBJECTEN).delete(ignore=404)
        Index(settings.ES_INDEX_ZO).delete(ignore=404)
        if init:
            ObjectDocument.init()
            ZaakObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_OBJECTEN).refresh()
        Index(settings.ES_INDEX_ZO).refresh()

    def setUp(self):
        super().setUp()
        objects = Service.objects.create(api_type=APITypes.orc, api_root=OBJECTS_ROOT)
        objecttypes = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = objects
        config.primary_objecttypes_api = objecttypes
        config.save()

    def test_index_objecten_no_zaken_index(self, m):
        self.clear_index(init=False)
        with self.assertRaises(NotFoundError):
            call_command("index_objecten")

    def test_index_objecten(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        objecttype = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e",
            "uuid": "1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e",
            "name": "Pand Utrecht NG",
            "namePlural": "Panden Utrecht NG",
            "description": "",
            "dataClassification": "open",
            "maintainerOrganization": "",
            "maintainerDepartment": "",
            "contactPerson": "",
            "contactEmail": "",
            "source": "",
            "updateFrequency": "unknown",
            "providerOrganization": "",
            "documentationUrl": "",
            "labels": {},
            "createdAt": "2023-01-02",
            "modifiedAt": "2023-01-02",
            "versions": [
                f"{OBJECTTYPES_ROOT}objecttypes/1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e/versions/1"
            ],
        }
        obj = {
            "url": f"{OBJECTS_ROOT}objects/f8a7573a-758f-4a19-aa22-245bb8f4712e",
            "uuid": "f8a7573a-758f-4a19-aa22-245bb8f4712e",
            "type": objecttype["url"],
            "record": {
                "index": 1,
                "typeVersion": 1,
                "data": {
                    "VELD": "1234",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [5.133365001529453, 52.07746853707585],
                },
                "startAt": "2022-12-15",
                "endAt": None,
                "registrationAt": "2022-12-15",
                "correctionFor": None,
                "correctedBy": None,
            },
        }
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=paginated_response([objecttype]))
        m.get(f"{OBJECTS_ROOT}objects", json=paginated_response([obj]))
        index = Index(settings.ES_INDEX_OBJECTEN)
        self.refresh_index()
        self.assertEqual(index.search().count(), 0)
        call_command("index_objecten")
        self.refresh_index()
        self.assertEqual(index.search().count(), 1)

    def test_index_objecten_relate_zaak(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        objecttype = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e",
            "uuid": "1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e",
            "name": "Pand Utrecht NG",
            "namePlural": "Panden Utrecht NG",
            "description": "",
            "dataClassification": "open",
            "maintainerOrganization": "",
            "maintainerDepartment": "",
            "contactPerson": "",
            "contactEmail": "",
            "source": "",
            "updateFrequency": "unknown",
            "providerOrganization": "",
            "documentationUrl": "",
            "labels": {},
            "createdAt": "2023-01-02",
            "modifiedAt": "2023-01-02",
            "versions": [
                f"{OBJECTTYPES_ROOT}objecttypes/1ddc6ea4-6d7f-4573-8f2d-6473eb1ceb5e/versions/1"
            ],
        }
        object = {
            "url": f"{OBJECTS_ROOT}objects/f8a7573a-758f-4a19-aa22-245bb8f4712e",
            "uuid": "f8a7573a-758f-4a19-aa22-245bb8f4712e",
            "type": objecttype["url"],
            "record": {
                "index": 1,
                "typeVersion": 1,
                "data": {
                    "VELD": "1234",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [5.133365001529453, 52.07746853707585],
                },
                "startAt": "2022-12-15",
                "endAt": None,
                "registrationAt": "2022-12-15",
                "correctionFor": None,
                "correctedBy": None,
            },
        }
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=paginated_response([objecttype]))
        m.get(f"{OBJECTS_ROOT}objects", json=paginated_response([object]))
        zaakobject = ZaakObjectDocument(
            url="http://zaken.nl/api/v1/zaakobjecten/f79989d3-9ac4-4c2b-a94e-13191b333444",
            object=object["url"],
            zaak="http://zaken.nl/api/v1/zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        )
        zaakobject.save()
        zd = ZaakDocument(
            url="http://zaken.nl/api/v1/zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            identificatie="some-identificatie",
            omschrijving="some-omschrijving",
            bronorganisatie="some-bronorganisatie",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            va_order=VA_ORDER[VertrouwelijkheidsAanduidingen.openbaar],
        )
        zd.save()
        index = Index(settings.ES_INDEX_OBJECTEN)
        self.refresh_index()
        self.assertEqual(index.search().count(), 0)
        with patch(
            "zac.elasticsearch.api.create_zaaktype_document", return_value=None
        ) as mock_create_ztd:
            call_command("index_objecten")
        mock_create_ztd.assert_called_once()

        self.refresh_index()
        self.assertEqual(index.search().count(), 1)
        self.assertEqual(
            index.search().execute()[0].related_zaken,
            [
                {
                    "url": "http://zaken.nl/api/v1/zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                    "bronorganisatie": "some-bronorganisatie",
                    "omschrijving": "some-omschrijving",
                    "identificatie": "some-identificatie",
                    "va_order": 114,
                }
            ],
        )
