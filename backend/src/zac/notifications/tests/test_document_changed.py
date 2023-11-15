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
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.datastructures import VA_ORDER
from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_informatieobject_document, create_iot_document
from zac.elasticsearch.documents import InformatieObjectDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get

from .utils import (
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    DRC_ROOT,
    INFORMATIEOBJECT,
    INFORMATIEOBJECT_RESPONSE,
    INFORMATIEOBJECTTYPE_RESPONSE,
)

NOTIFICATION_CREATE = {
    "kanaal": "documenten",
    "hoofdObject": INFORMATIEOBJECT,
    "resource": "enkelvoudiginformatieobject",
    "resourceUrl": INFORMATIEOBJECT,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}
NOTIFICATION_UPDATE = {
    "kanaal": "documenten",
    "hoofdObject": INFORMATIEOBJECT,
    "resource": "enkelvoudiginformatieobject",
    "resourceUrl": INFORMATIEOBJECT,
    "actie": "update",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}
NOTIFICATION_DESTROY = {
    "kanaal": "documenten",
    "hoofdObject": INFORMATIEOBJECT,
    "resource": "enkelvoudiginformatieobject",
    "resourceUrl": INFORMATIEOBJECT,
    "actie": "destroy",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {},
}


@requests_mock.Mocker()
class InformatieObjectChangedTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
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
        Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        Service.objects.create(api_root=DRC_ROOT, api_type=APITypes.drc)

        # config = CoreConfig.get_solo()
        # config.save()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

    def _setup_mocks(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, DRC_ROOT, "drc")
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, INFORMATIEOBJECT_RESPONSE)
        mock_resource_get(rm, INFORMATIEOBJECTTYPE_RESPONSE)

    def test_informatieobject_created_indexed_in_es(self, rm):
        self._setup_mocks(rm)
        rm.get(f"{INFORMATIEOBJECT_RESPONSE['url']}/audittrail", status_code=404)

        # assert IO is not indexed
        with self.assertRaises(NotFoundError):
            InformatieObjectDocument.get(
                id=INFORMATIEOBJECT_RESPONSE["url"].split("/")[-1]
            )

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_CREATE)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.refresh_index()
        InformatieObjectDocument.get(id=INFORMATIEOBJECT_RESPONSE["url"].split("/")[-1])

    def test_informatieobject_updated_in_es(self, rm):
        self._setup_mocks(rm)

        io = factory(Document, INFORMATIEOBJECT_RESPONSE)
        io.informatieobjecttype = factory(
            InformatieObjectType, INFORMATIEOBJECTTYPE_RESPONSE
        )
        io_document = create_informatieobject_document(io)
        io_document.informatieobjecttype = create_iot_document(io.informatieobjecttype)
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

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_UPDATE)
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
        io_document = create_informatieobject_document(io)
        io_document.informatieobjecttype = create_iot_document(io.informatieobjecttype)
        io_document.save()
        self.refresh_index()

        # Assert exists
        io_document = InformatieObjectDocument.get(
            id=INFORMATIEOBJECT_RESPONSE["url"].split("/")[-1]
        )

        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION_DESTROY)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.refresh_index()

        # assert IO is not indexed
        with self.assertRaises(NotFoundError):
            InformatieObjectDocument.get(
                id=INFORMATIEOBJECT_RESPONSE["url"].split("/")[-1]
            )
