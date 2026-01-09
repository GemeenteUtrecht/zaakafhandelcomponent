from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.models import AccessRequest
from zac.accounts.tests.factories import AccessRequestFactory, UserFactory
from zac.activities.models import Activity, Event
from zac.activities.tests.factories import ActivityFactory, EventFactory
from zac.contrib.board.models import BoardItem
from zac.contrib.board.tests.factories import BoardItemFactory
from zac.elasticsearch.api import create_zaak_document
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import mock_service_oas_get
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    STATUS_RESPONSE,
    STATUSTYPE_RESPONSE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

# UPDATED: snake_case keys
NOTIFICATION = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "zaak",
    "resource_url": ZAAK,
    "actie": "destroy",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}


class ZaakDestroyedTests(ESMixin, APITestCase):
    """
    Test that the appropriate actions happen on zaak-destroyed notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create(username="notifs")
        cls.ztc = Service.objects.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        cls.zrc = Service.objects.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_ad_hoc_activities_deleted(self):
        path = reverse("notifications:callback")

        activity = ActivityFactory.create(
            zaak=f"{ZAKEN_ROOT}zaken/f3ff2713-2f53-42ff-a154-16842309ad60"
        )
        EventFactory.create(activity=activity)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Activity.objects.exists())
        self.assertFalse(Event.objects.exists())

    @requests_mock.Mocker()
    def test_remove_es_document(self, rm, *mocks):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, STATUS_RESPONSE)
        mock_resource_get(rm, STATUSTYPE_RESPONSE)

        path = reverse("notifications:callback")

        # create zaak document in ES
        zaak = factory(
            Zaak, {**ZAAK_RESPONSE, "zaaktype": factory(ZaakType, ZAAKTYPE_RESPONSE)}
        )
        zaak_document = create_zaak_document(zaak)
        self.refresh_index()

        zaak_document.save()
        self.assertEqual(
            str(zaak_document.meta.id), "f3ff2713-2f53-42ff-a154-16842309ad60"
        )

        response = self.client.post(path, NOTIFICATION)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id, ignore=404)
        self.assertIsNone(zaak_document)

    def test_board_item_deleted(self):
        path = reverse("notifications:callback")
        BoardItemFactory(object=ZAAK)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(BoardItem.objects.exists())

    def test_access_request_deleted(self):
        path = reverse("notifications:callback")
        AccessRequestFactory(zaak=ZAAK)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AccessRequest.objects.exists())
