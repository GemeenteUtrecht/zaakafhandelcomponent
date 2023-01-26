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
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.datastructures import VA_ORDER
from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import (
    _get_uuid_from_url,
    create_informatieobject_document,
    create_related_zaak_document,
    create_zaak_document,
    create_zaakinformatieobject_document,
    create_zaaktype_document,
)
from zac.elasticsearch.documents import InformatieObjectDocument, ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak, ZaakInformatieObject

from .utils import (
    CATALOGI_ROOT,
    DRC_ROOT,
    INFORMATIEOBJECT,
    INFORMATIEOBJECT_RESPONSE,
    INFORMATIEOBJECTTYPE_RESPONSE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKINFORMATIEOBJECT,
    ZAAKINFORMATIEOBJECT_RESPONSE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

NOTIFICATION_CREATE = {
    "kanaal": "zaken",
    "hoofdObject": ZAAK,
    "resource": "zaakinformatieobject",
    "resourceUrl": ZAAKINFORMATIEOBJECT,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}
NOTIFICATION_DESTROY = {
    "kanaal": "zaken",
    "hoofdObject": ZAAK,
    "resource": "zaakinformatieobject",
    "resourceUrl": ZAAKINFORMATIEOBJECT,
    "actie": "destroy",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}


@requests_mock.Mocker()
class ZaakInformatieObjectChangedTests(
    ClearCachesMixin, ESMixin, APITransactionTestCase
):
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
        Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        Service.objects.create(api_root=DRC_ROOT, api_type=APITypes.drc)

        # config = CoreConfig.get_solo()
        # config.save()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

    def _setup_mocks(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, DRC_ROOT, "drc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, INFORMATIEOBJECT_RESPONSE)
        mock_resource_get(rm, INFORMATIEOBJECTTYPE_RESPONSE)
        rm.get(
            f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([ZAAKTYPE_RESPONSE])
        )

    def test_zaakinformatieobject_created_indexed_in_es(self, rm):
        self._setup_mocks(rm)
        mock_resource_get(rm, ZAAKINFORMATIEOBJECT_RESPONSE)
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={ZAAK}",
            json=[ZAAKINFORMATIEOBJECT_RESPONSE],
        )
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?informatieobject={INFORMATIEOBJECT}",
            json=[ZAAKINFORMATIEOBJECT_RESPONSE],
        )

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaaktype_document(zaak.zaaktype)
        zaak_document.save()
        self.refresh_index()

        # Assert no zaakinformatieobject is connected to it
        self.assertEqual(zaak_document.zaakinformatieobjecten, [])

        # Assert no object document is found with the object uuid
        with self.assertRaises(NotFoundError):
            InformatieObjectDocument.get(id=_get_uuid_from_url(INFORMATIEOBJECT))

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_CREATE)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(
            zaak_document.zaakinformatieobjecten,
            [
                {
                    "url": ZAAKINFORMATIEOBJECT,
                    "informatieobject": INFORMATIEOBJECT,
                }
            ],
        )

        informatieobject_document = InformatieObjectDocument.get(
            id=_get_uuid_from_url(INFORMATIEOBJECT)
        )
        self.assertEqual(
            informatieobject_document.related_zaken,
            [
                {
                    "url": ZAAK,
                    "bronorganisatie": ZAAK_RESPONSE["bronorganisatie"],
                    "omschrijving": ZAAK_RESPONSE["omschrijving"],
                    "identificatie": ZAAK_RESPONSE["identificatie"],
                    "va_order": VA_ORDER[ZAAK_RESPONSE["vertrouwelijkheidaanduiding"]],
                    "zaaktype": {
                        "url": ZAAKTYPE_RESPONSE["url"],
                        "catalogus": ZAAKTYPE_RESPONSE["catalogus"],
                        "omschrijving": ZAAKTYPE_RESPONSE["omschrijving"],
                        "identificatie": ZAAKTYPE_RESPONSE["identificatie"],
                    },
                }
            ],
        )

    def test_zaakinformatieobject_destroyed_in_es(self, rm):
        self._setup_mocks(rm)
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={ZAAK}",
            json=[],
        )
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?informatieobject={INFORMATIEOBJECT}",
            json=[],
        )

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaaktype_document(zaak.zaaktype)
        zaak_document.zaakinformatieobjecten = [
            create_zaakinformatieobject_document(
                factory(ZaakInformatieObject, ZAAKINFORMATIEOBJECT_RESPONSE)
            )
        ]
        zaak_document.save()
        self.refresh_index()

        # Assert zaakobject is connected to it
        self.assertEqual(
            zaak_document.zaakinformatieobjecten,
            [
                {
                    "url": ZAAKINFORMATIEOBJECT,
                    "informatieobject": INFORMATIEOBJECT,
                }
            ],
        )

        # create informatieobject document
        informatieobject_document = create_informatieobject_document(
            factory(Document, INFORMATIEOBJECT_RESPONSE)
        )
        informatieobject_document.related_zaken = [create_related_zaak_document(zaak)]
        informatieobject_document.save()

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_DESTROY)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Assert zaakinformatieobjecten is empty
        self.refresh_index()
        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(zaak_document.zaakinformatieobjecten, [])

        # Assert related_zaken of informatieobject document is empty.
        informatieobject_document = InformatieObjectDocument.get(
            id=_get_uuid_from_url(INFORMATIEOBJECT)
        )
        self.assertEqual(informatieobject_document.related_zaken, [])
