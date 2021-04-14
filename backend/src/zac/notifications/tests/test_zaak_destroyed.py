from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType

from zac.accounts.tests.factories import UserFactory
from zac.activities.models import Activity, Event
from zac.activities.tests.factories import ActivityFactory, EventFactory
from zac.elasticsearch.api import create_zaak_document
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zgw.models.zrc import Zaak

from .utils import BRONORGANISATIE, ZAAK_RESPONSE, ZAAKTYPE, ZAAKTYPE_RESPONSE

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

    def test_remove_es_document(self):
        path = reverse("notifications:callback")
        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        self.assertEqual(zaak_document.meta.id, "f3ff2713-2f53-42ff-a154-16842309ad60")

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id, ignore=404)
        self.assertIsNone(zaak_document)
