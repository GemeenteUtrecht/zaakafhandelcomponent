from copy import deepcopy

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.datastructures import VA_ORDER
from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import (
    _get_uuid_from_url,
    create_informatieobject_document,
    create_related_zaak_document,
    update_zaakinformatieobject_document,
)
from zac.elasticsearch.documents import (
    InformatieObjectDocument,
    ZaakInformatieObjectDocument,
)
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak, ZaakInformatieObject

from .utils import (
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
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

# UPDATED: snake_case keys
NOTIFICATION_CREATE = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "zaakinformatieobject",
    "resource_url": ZAAKINFORMATIEOBJECT,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}
NOTIFICATION_UPDATE = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "zaakinformatieobject",
    "resource_url": ZAAKINFORMATIEOBJECT,
    "actie": "update",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}
NOTIFICATION_DESTROY = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "zaakinformatieobject",
    "resource_url": ZAAKINFORMATIEOBJECT,
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
        Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        Service.objects.create(api_root=DRC_ROOT, api_type=APITypes.drc)
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

    def _setup_mocks(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(rm, DRC_ROOT, "drc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
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
            f"{ZAKEN_ROOT}zaakinformatieobjecten?informatieobject={INFORMATIEOBJECT}",
            json=[ZAAKINFORMATIEOBJECT_RESPONSE],
        )
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={ZAAK}",
            json=[ZAAKINFORMATIEOBJECT_RESPONSE],
        )
        rm.get(f"{INFORMATIEOBJECT_RESPONSE['url']}/audittrail", status_code=404)

        # Assert not present
        with self.assertRaises(NotFoundError):
            ZaakInformatieObjectDocument.get(
                id=_get_uuid_from_url(ZAAKINFORMATIEOBJECT)
            )
        with self.assertRaises(NotFoundError):
            InformatieObjectDocument.get(id=_get_uuid_from_url(INFORMATIEOBJECT))

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_CREATE)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        ZaakInformatieObjectDocument.get(id=_get_uuid_from_url(ZAAKINFORMATIEOBJECT))
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
                        "catalogus_domein": CATALOGUS_RESPONSE["domein"],
                        "omschrijving": ZAAKTYPE_RESPONSE["omschrijving"],
                        "identificatie": ZAAKTYPE_RESPONSE["identificatie"],
                    },
                }
            ],
        )

    def test_zaakinformatieobject_updated_in_es(self, rm):
        self._setup_mocks(rm)
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={ZAAK}",
            json=[ZAAKINFORMATIEOBJECT_RESPONSE],
        )
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?informatieobject={INFORMATIEOBJECT}",
            json=[],
        )
        zaak = factory(Zaak, ZAAK_RESPONSE)
        update_zaakinformatieobject_document(
            factory(ZaakInformatieObject, ZAAKINFORMATIEOBJECT_RESPONSE)
        )
        self.refresh_index()

        # Assert exists
        ZaakInformatieObjectDocument.get(id=_get_uuid_from_url(ZAAKINFORMATIEOBJECT))

        document = factory(Document, INFORMATIEOBJECT_RESPONSE)
        document.informatieobjecttype = factory(
            InformatieObjectType, INFORMATIEOBJECTTYPE_RESPONSE
        )
        document.last_edited_date = None

        # create informatieobject document
        informatieobject_document = create_informatieobject_document(document)
        informatieobject_document.related_zaken = [create_related_zaak_document(zaak)]
        informatieobject_document.save()

        # mock new situation where zio is updated
        rm.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={ZAAK}", json=[])

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_DESTROY)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Assert emptied
        self.refresh_index()
        with self.assertRaises(NotFoundError):
            ZaakInformatieObjectDocument.get(
                id=_get_uuid_from_url(ZAAKINFORMATIEOBJECT)
            )

        informatieobject_document = InformatieObjectDocument.get(
            id=_get_uuid_from_url(INFORMATIEOBJECT)
        )
        self.assertEqual(informatieobject_document.related_zaken, [])

    def test_zaakinformatieobject_destroyed_in_es(self, rm):
        self._setup_mocks(rm)
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={ZAAK}",
            json=[ZAAKINFORMATIEOBJECT_RESPONSE],
        )
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?informatieobject={INFORMATIEOBJECT}",
            json=[],
        )
        zaak = factory(Zaak, ZAAK_RESPONSE)
        update_zaakinformatieobject_document(
            factory(ZaakInformatieObject, ZAAKINFORMATIEOBJECT_RESPONSE)
        )
        self.refresh_index()

        # Assert exists
        ZaakInformatieObjectDocument.get(id=_get_uuid_from_url(ZAAKINFORMATIEOBJECT))

        # create informatieobject document
        document = factory(Document, INFORMATIEOBJECT_RESPONSE)
        document.informatieobjecttype = factory(
            InformatieObjectType, INFORMATIEOBJECTTYPE_RESPONSE
        )
        document.last_edited_date = None
        informatieobject_document = create_informatieobject_document(document)
        informatieobject_document.related_zaken = [create_related_zaak_document(zaak)]
        informatieobject_document.save()

        # mock new situation where zio is deleted
        rm.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={ZAAK}", json=[])

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_DESTROY)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Assert emptied
        self.refresh_index()
        with self.assertRaises(NotFoundError):
            ZaakInformatieObjectDocument.get(
                id=_get_uuid_from_url(ZAAKINFORMATIEOBJECT)
            )

        informatieobject_document = InformatieObjectDocument.get(
            id=_get_uuid_from_url(INFORMATIEOBJECT)
        )
        self.assertEqual(informatieobject_document.related_zaken, [])
