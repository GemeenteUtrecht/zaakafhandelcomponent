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
from zgw_consumers.api_models.catalogi import InformatieObjectType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.datastructures import VA_ORDER
from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.elasticsearch.api import create_informatieobject_document
from zac.elasticsearch.documents import InformatieObjectDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response

from .utils import (
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    DRC_ROOT,
    INFORMATIEOBJECT,
    INFORMATIEOBJECT_RESPONSE,
    INFORMATIEOBJECTTYPE_RESPONSE,
    ZAAK_RESPONSE,
    ZAAKINFORMATIEOBJECT_RESPONSE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

# Updated to snake_case keys expected by the refactored handlers
NOTIFICATION_CREATE = {
    "kanaal": "documenten",
    "hoofd_object": INFORMATIEOBJECT,
    "resource": "enkelvoudiginformatieobject",
    "resource_url": INFORMATIEOBJECT,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}
NOTIFICATION_UPDATE = {
    "kanaal": "documenten",
    "hoofd_object": INFORMATIEOBJECT,
    "resource": "enkelvoudiginformatieobject",
    "resource_url": INFORMATIEOBJECT,
    "actie": "update",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}
NOTIFICATION_DESTROY = {
    "kanaal": "documenten",
    "hoofd_object": INFORMATIEOBJECT,
    "resource": "enkelvoudiginformatieobject",
    "resource_url": INFORMATIEOBJECT,
    "actie": "destroy",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}


@requests_mock.Mocker()
class InformatieObjectChangedTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    @staticmethod
    def clear_index(init: bool = False):
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
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        Service.objects.create(api_root=DRC_ROOT, api_type=APITypes.drc)
        Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

    def _setup_mocks(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, DRC_ROOT, "drc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, INFORMATIEOBJECT_RESPONSE)
        mock_resource_get(rm, INFORMATIEOBJECTTYPE_RESPONSE)

    def test_informatieobject_created_indexed_in_es(self, rm):
        self._setup_mocks(rm)
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        rm.get(f"{INFORMATIEOBJECT_RESPONSE['url']}/audittrail", status_code=404)
        rm.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?informatieobject={INFORMATIEOBJECT}",
            json=[ZAAKINFORMATIEOBJECT_RESPONSE],
        )
        rm.get(
            f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([ZAAKTYPE_RESPONSE])
        )

        # assert IO is not indexed
        with self.assertRaises(NotFoundError):
            InformatieObjectDocument.get(
                id=INFORMATIEOBJECT_RESPONSE["url"].split("/")[-1]
            )

        url = reverse("notifications:callback")
        with patch("zac.elasticsearch.api.parallel", return_value=mock_parallel()):
            response = self.client.post(url, NOTIFICATION_CREATE)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.refresh_index()
        eio_doc = InformatieObjectDocument.get(
            id=INFORMATIEOBJECT_RESPONSE["url"].split("/")[-1]
        )
        self.assertEqual(eio_doc.related_zaken[0].url, ZAAK_RESPONSE["url"])

    def test_informatieobject_updated_in_es(self, rm):
        self._setup_mocks(rm)

        io = factory(Document, INFORMATIEOBJECT_RESPONSE)
        io.informatieobjecttype = factory(
            InformatieObjectType, INFORMATIEOBJECTTYPE_RESPONSE
        )
        io.last_edited_date = None
        io_document = create_informatieobject_document(io)
        io_document.save()
        self.refresh_index()

        # Assert last edited date
        io_document = InformatieObjectDocument.get(id=io_document.meta.id)
        self.assertEqual(io_document.last_edited_date, None)

        audit_trail = generate_oas_component(
            "drc",
            "schemas/AuditTrail",
            hoofdObject=INFORMATIEOBJECT_RESPONSE["url"],
            resourceUrl=INFORMATIEOBJECT_RESPONSE["url"],
            wijzigingen={
                "oud": {
                    "content": "",
                    "modified": "2022-03-04T12:11:21.157+01:00",
                    "author": "ONBEKEND",
                    "versionLabel": "0.2",
                },
                "nieuw": {
                    "content": "",
                    "modified": "2022-03-04T12:11:39.293+01:00",
                    "author": "John Doe",
                    "versionLabel": "0.3",
                },
            },
        )
        rm.get(f"{INFORMATIEOBJECT_RESPONSE['url']}/audittrail", json=[audit_trail])

        url = reverse("notifications:callback")
        response = self.client.post(url, NOTIFICATION_UPDATE)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.refresh_index()
        io_document = InformatieObjectDocument.get(id=io_document.meta.id)
        self.assertEqual(
            io_document.last_edited_date.isoformat(), "2022-03-04T12:11:39.293000+01:00"
        )

    def test_informatieobject_destroyed_in_es(self, rm):
        self._setup_mocks(rm)

        io = factory(Document, INFORMATIEOBJECT_RESPONSE)
        io.informatieobjecttype = factory(
            InformatieObjectType, INFORMATIEOBJECTTYPE_RESPONSE
        )

        io.last_edited_date = None
        io_document = create_informatieobject_document(io)
        io_document.save()
        self.refresh_index()

        # Assert exists
        _ = InformatieObjectDocument.get(
            id=INFORMATIEOBJECT_RESPONSE["url"].split("/")[-1]
        )

        url = reverse("notifications:callback")
        response = self.client.post(url, NOTIFICATION_DESTROY)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.refresh_index()

        # assert IO is not indexed
        with self.assertRaises(NotFoundError):
            InformatieObjectDocument.get(
                id=INFORMATIEOBJECT_RESPONSE["url"].split("/")[-1]
            )
