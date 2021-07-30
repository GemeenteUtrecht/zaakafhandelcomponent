from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.tests.factories import UserFactory
from zac.activities.models import Activity, Event
from zac.activities.tests.factories import ActivityFactory, EventFactory
from zac.elasticsearch.api import create_zaak_document
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zgw.models.zrc import Zaak

from .utils import (
    BRONORGANISATIE,
    STATUS,
    STATUS_RESPONSE,
    STATUSTYPE,
    STATUSTYPE_RESPONSE,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
)

NOTIFICATION = {
    "kanaal": "zaken",
    "hoofdObject": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
    "resource": "zaak",
    "resourceUrl": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
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
        cls.ztc = Service.objects.create(
            api_root="https://some.ztc.nl/api/v1/", api_type=APITypes.ztc
        )
        cls.zrc = Service.objects.create(
            api_root="https://some.zrc.nl/api/v1/", api_type=APITypes.zrc
        )

    def setUp(self):
        super().setUp()

        self.client.force_authenticate(user=self.user)

    def test_ad_hoc_activities_deleted(self):
        path = reverse("notifications:callback")

        activity = ActivityFactory.create(
            zaak="https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60"
        )
        EventFactory.create(activity=activity)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Activity.objects.exists())
        self.assertFalse(Event.objects.exists())

    @requests_mock.Mocker()
    def test_remove_es_document(self, rm):
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zrc")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(STATUS, json=STATUS_RESPONSE)
        rm.get(STATUSTYPE, json=STATUSTYPE_RESPONSE)
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)

        path = reverse("notifications:callback")

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        self.assertEqual(zaak_document.meta.id, "f3ff2713-2f53-42ff-a154-16842309ad60")

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id, ignore=404)
        self.assertIsNone(zaak_document)
