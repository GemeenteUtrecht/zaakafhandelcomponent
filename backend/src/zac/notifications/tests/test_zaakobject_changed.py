from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.models import APITypes, Service

from zac.accounts.tests.factories import UserFactory
from zac.core.services import get_zaakobjecten
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from .utils import (
    BRONORGANISATIE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
    mock_service_oas_get,
)

ZAKEN_ROOT = "https://some.zrc.nl/api/v1/"
CATALOGI_ROOT = "https://some.ztc.nl/api/v1/"

NOTIFICATION = {
    "kanaal": "zaken",
    "hoofdObject": ZAAK,
    "resource": "zaakobject",
    "resourceUrl": f"{ZAKEN_ROOT}zaakobjecten/f3ff2713-2f53-42ff-a154-16842309ad60",
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}

ZAAKOBJECT1 = {
    "url": f"{ZAKEN_ROOT}zaakobjecten/4abe87ea-3670-42c8-afc7-5e9fb071971d",
    "object": "https://objects.nl/api/v1/objects/aa44d251-0ddc-4bf2-b114-00a5ce1925d1",
    "zaak": ZAAK_RESPONSE["url"],
    "object_type": "some-object-type",
    "object_type_overige": "",
    "relatieomschrijving": "",
    "object_identificatie": {},
}
ZAAKOBJECT2 = {
    "url": f"{ZAKEN_ROOT}zaakobjecten/5abe87ea-3670-42c8-afc7-5e9fb071971d",
    "object": "https://objects.nl/api/v1/objects/ba44d251-0ddc-4bf2-b114-00a5ce1925d1",
    "zaak": ZAAK_RESPONSE["url"],
    "object_type": "",
    "object_type_overige": "",
    "relatieomschrijving": "",
    "object_identificatie": {},
}


@requests_mock.Mocker()
class ZaakObjectCreatedTests(APITestCase):
    """
    Test that the appropriate actions happen on status creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create(username="notifs")
        cls.ztc = Service.objects.create(
            api_root="https://some.ztc.nl/api/v1/", api_type=APITypes.ztc
        )
        cls.zrc = Service.objects.create(
            api_root=f"{ZAKEN_ROOT}", api_type=APITypes.zrc
        )

    def setUp(self):
        super().setUp()

        cache.clear()
        self.client.force_authenticate(user=self.user)

    def test_zaakobject_changed(self, rm):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zaken")
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        ZAAK_RESPONSE["status"] = None
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)

        path = reverse("notifications:callback")

        # Mock get_zaakobjecten call
        rm.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={ZAAK}",
            json=paginated_response([ZAAKOBJECT1]),
        )
        zaakobject1 = get_zaakobjecten(factory(Zaak, ZAAK_RESPONSE))

        # Mock get_zaakobjecten call with different response to show cache is hit
        rm.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={ZAAK}",
            json=paginated_response([ZAAKOBJECT2]),
        )
        zaakobject2 = get_zaakobjecten(factory(Zaak, ZAAK_RESPONSE))

        # Cache was hit - so results should be equal
        self.assertEqual(zaakobject1, zaakobject2)

        # Send out notification - wiping the cache for this specific get_zaakobjecten call
        response = self.client.post(path, NOTIFICATION)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        number_of_requests = len(rm.request_history)

        # Call again - this time the new zaakobject shall be returned as it is now cached as such
        zaakobject2 = get_zaakobjecten(factory(Zaak, ZAAK_RESPONSE))

        number_of_requests_after = len(rm.request_history)
        self.assertEqual(number_of_requests, number_of_requests_after)
        self.assertNotEqual(zaakobject1, zaakobject2)
