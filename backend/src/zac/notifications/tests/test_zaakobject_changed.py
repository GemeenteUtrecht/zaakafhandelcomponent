from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

import requests_mock
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.zaken import ZaakObject
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.models import User
from zac.accounts.tests.factories import UserFactory
from zac.core.models import CoreConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import (
    create_object_document,
    create_related_zaak_document,
    create_zaak_document,
    create_zaakobject_document,
    create_zaaktype_document,
)
from zac.elasticsearch.documents import ObjectDocument, ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from .utils import (
    CATALOGI_ROOT,
    OBJECT_RESPONSE,
    OBJECTS_ROOT,
    OBJECTTYPE_RESPONSE,
    OBJECTTYPE_VERSION_RESPONSE,
    OBJECTTYPES_ROOT,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

OBJECT = OBJECT_RESPONSE["url"]
ZAAKOBJECT = f"{ZAKEN_ROOT}zaakobjecten/69e98129-1f0d-497f-bbfb-84b88137edbc"
NOTIFICATION_CREATE = {
    "kanaal": "zaken",
    "hoofdObject": ZAAK,
    "resource": "zaakobject",
    "resourceUrl": ZAAKOBJECT,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "object": OBJECT,
    },
}
NOTIFICATION_DESTROY = {
    "kanaal": "zaken",
    "hoofdObject": ZAAK,
    "resource": "zaakobject",
    "resourceUrl": ZAAKOBJECT,
    "actie": "destroy",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "object": OBJECT,
    },
}


@requests_mock.Mocker()
class ZaakObjectChangedTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
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
        Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        objects_service = Service.objects.create(
            api_root=OBJECTS_ROOT, api_type=APITypes.orc
        )
        objecttypes_service = Service.objects.create(
            api_root=OBJECTTYPES_ROOT, api_type=APITypes.orc
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = objects_service
        config.primary_objecttypes_api = objecttypes_service
        config.save()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

    def _setup_mocks(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, OBJECTS_ROOT, "objects")
        mock_service_oas_get(rm, OBJECTTYPES_ROOT, "objecttypes")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, OBJECT_RESPONSE)
        mock_resource_get(rm, OBJECTTYPE_RESPONSE)
        mock_resource_get(rm, OBJECTTYPE_VERSION_RESPONSE)
        self.zo = generate_oas_component(
            "zrc",
            "schemas/ZaakObject",
            url=ZAAKOBJECT,
            object=OBJECT,
            zaak=ZAAK,
            object_identificatie=None,
        )

    def test_zaakobject_created_indexed_in_es(self, rm, *mocks):
        self._setup_mocks(rm)
        mock_resource_get(rm, self.zo)
        rm.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={ZAAK}",
            json=paginated_response([self.zo]),
        )
        rm.get(
            f"{ZAKEN_ROOT}zaakobjecten?object={OBJECT}",
            json=paginated_response([self.zo]),
        )

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaaktype_document(zaak.zaaktype)
        zaak_document.save()
        self.refresh_index()

        # Assert no zaakobject is connected to it
        self.assertEqual(zaak_document.zaakobjecten, [])

        # Assert no object document is found with the object uuid
        with self.assertRaises(NotFoundError):
            ObjectDocument.get(id=OBJECT_RESPONSE["uuid"])

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_CREATE)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(
            zaak_document.zaakobjecten,
            [
                {
                    "url": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60/zaakobjecten/69e98129-1f0d-497f-bbfb-84b88137edbc",
                    "object": "https://some.objects.nl/api/v1/objects/f8a7573a-758f-4a19-aa22-245bb8f4712e",
                }
            ],
        )

        object_document = ObjectDocument.get(id=OBJECT_RESPONSE["uuid"])
        self.assertEqual(
            object_document.related_zaken,
            [
                {
                    "url": ZAAK,
                    "bronorganisatie": ZAAK_RESPONSE["bronorganisatie"],
                    "omschrijving": ZAAK_RESPONSE["omschrijving"],
                    "identificatie": ZAAK_RESPONSE["identificatie"],
                }
            ],
        )

    def test_zaakobject_destroyed_in_es(self, rm, *mocks):
        self._setup_mocks(rm)
        rm.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={ZAAK}",
            json=paginated_response([]),
        )
        rm.get(
            f"{ZAKEN_ROOT}zaakobjecten?object={OBJECT}",
            json=paginated_response([]),
        )

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaaktype_document(zaak.zaaktype)
        zaak_document.zaakobjecten = [
            create_zaakobject_document(factory(ZaakObject, self.zo))
        ]
        zaak_document.save()
        self.refresh_index()

        # Assert zaakobject is connected to it
        self.assertEqual(
            zaak_document.zaakobjecten,
            [
                {
                    "url": self.zo["url"],
                    "object": self.zo["object"],
                }
            ],
        )

        # create object document
        object_document = create_object_document(OBJECT_RESPONSE)
        object_document.related_zaken = [create_related_zaak_document(zaak)]
        object_document.save()

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_DESTROY)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        zaak_document.refresh()
        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)

        # Assert zaakobjecten is empty
        self.assertEqual(zaak_document.zaakobjecten, [])

        # Assert related_zaken of object document is empty.
        object_document = ObjectDocument.get(id=OBJECT_RESPONSE["uuid"])
        self.assertEqual(object_document.related_zaken, [])
