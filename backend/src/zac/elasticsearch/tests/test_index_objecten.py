from django.conf import settings
from django.core.management import call_command

import requests_mock
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from rest_framework.test import APITransactionTestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from zac.core.models import CoreConfig
from zac.core.tests.utils import ClearCachesMixin

from ..documents import ObjectDocument, ZaakDocument, ZaakObjectDocument
from .utils import ESMixin

OBJECTS_ROOT = "https://api.objects.nl/api/v1/"
OBJECTTYPES_ROOT = "https://api.objecttypes.nl/api/v1/"


@requests_mock.Mocker()
class IndexObjectsTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_OBJECTEN).delete(ignore=404)

        if init:
            ObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_OBJECTEN).refresh()

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
            "url": f"{OBJECTTYPES_ROOT}objecttypes/1",
            "name": "laadpaal",
            "namePlural": "laadpalen",
            "description": "",
            "data_classification": "",
            "maintainer_organization": "",
            "maintainer_department": "",
            "contact_person": "",
            "contact_email": "",
            "source": "",
            "update_frequency": "",
            "provider_organization": "",
            "documentation_url": "",
            "labels": {},
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "versions": [],
        }
        object = {
            "url": f"{OBJECTS_ROOT}objects/e0346ea0-75aa-47e0-9283-cfb35963b725",
            "type": f"{OBJECTTYPES_ROOT}objecttypes/1",
            "record": {
                "index": 1,
                "typeVersion": 1,
                "data": {
                    "type": "Laadpaal",
                    "adres": "Utrechtsestraat 41",
                    "status": "Laadpaal in ontwikkeling",
                    "objectid": 2,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [5.114160150114911, 52.08850095597628],
                },
                "startAt": "2021-07-09",
                "endAt": None,
                "registrationAt": "2021-07-09",
                "correctionFor": None,
                "correctedBy": None,
            },
        }
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[objecttype])
        m.get(f"{OBJECTS_ROOT}objects", json=[object])
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
            "url": f"{OBJECTTYPES_ROOT}objecttypes/1",
            "name": "laadpaal",
            "namePlural": "laadpalen",
            "description": "",
            "data_classification": "",
            "maintainer_organization": "",
            "maintainer_department": "",
            "contact_person": "",
            "contact_email": "",
            "source": "",
            "update_frequency": "",
            "provider_organization": "",
            "documentation_url": "",
            "labels": {},
            "created_at": "2019-08-24",
            "modified_at": "2019-08-24",
            "versions": [],
        }
        object = {
            "url": f"{OBJECTS_ROOT}objects/e0346ea0-75aa-47e0-9283-cfb35963b725",
            "type": f"{OBJECTTYPES_ROOT}objecttypes/1",
            "record": {
                "index": 1,
                "typeVersion": 1,
                "data": {
                    "type": "Laadpaal",
                    "adres": "Utrechtsestraat 41",
                    "status": "Laadpaal in ontwikkeling",
                    "objectid": 2,
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [5.114160150114911, 52.08850095597628],
                },
                "startAt": "2021-07-09",
                "endAt": None,
                "registrationAt": "2021-07-09",
                "correctionFor": None,
                "correctedBy": None,
            },
        }
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[objecttype])
        m.get(f"{OBJECTS_ROOT}objects", json=[object])
        zaakobject = ZaakObjectDocument(
            url="https://some-url.com/", object=object["url"]
        )
        zd = ZaakDocument(
            identificatie="some-identificatie",
            omschrijving="some-omschrijving",
            bronorganisatie="some-bronorganisatie",
            zaakobjecten=[zaakobject],
        )
        zd.save()
        index = Index(settings.ES_INDEX_OBJECTEN)
        self.refresh_index()
        self.assertEqual(index.search().count(), 0)
        call_command("index_objecten")
        self.refresh_index()
        self.assertEqual(index.search().count(), 1)
        self.assertEqual(
            index.search().execute()[0].related_zaken,
            [
                {
                    "identificatie": "some-identificatie",
                    "omschrijving": "some-omschrijving",
                    "bronorganisatie": "some-bronorganisatie",
                }
            ],
        )
