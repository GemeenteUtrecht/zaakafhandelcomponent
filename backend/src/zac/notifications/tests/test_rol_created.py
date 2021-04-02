from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.models import APITypes, Service

from zac.accounts.constants import PermissionObjectType
from zac.accounts.models import AtomicPermission, User
from zac.core.permissions import zaken_inzien
from zac.elasticsearch.api import create_zaak_document
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zgw.models import Zaak

from .utils import (
    BRONORGANISATIE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
    mock_service_oas_get,
)

ROL = "https://some.zrc.nl/api/v1/rollen/69e98129-1f0d-497f-bbfb-84b88137edbc"
NOTIFICATION = {
    "kanaal": "zaken",
    "hoofdObject": ZAAK,
    "resource": "rol",
    "resourceUrl": ROL,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}


@requests_mock.Mocker()
class RolCreatedTests(ESMixin, APITestCase):
    """
    Test that the appropriate actions happen on zaak-creation notifications.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.zrc = Service.objects.create(
            api_root="https://some.zrc.nl/api/v1/", api_type=APITypes.zrc
        )

    def setUp(self):
        super().setUp()

        cache.clear()
        self.client.force_authenticate(user=self.user)

    def test_rol_created_indexed_in_es(self, rm):
        path = reverse("notifications:callback")
        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)
        self.assertEqual(zaak_document.rollen, [])

        # set up mocks
        rol = {
            "url": ROL,
            "zaak": ZAAK,
            "betrokkene": None,
            "betrokkeneType": "organisatorische_eenheid",
            "roltype": "https://some.ztc.nl/api/v1/roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": "123456",
            },
        }
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        rm.get(
            f"https://some.zrc.nl/api/v1/rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )
        rm.get(ROL, json=rol)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], ROL)

    def test_rol_created_add_permission_for_behandelaar(self, rm):
        path = reverse("notifications:callback")
        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        create_zaak_document(zaak)
        # set up mocks
        rol = {
            "url": ROL,
            "zaak": ZAAK,
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": "https://some.ztc.nl/api/v1/roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
            },
        }
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        rm.get(
            f"https://some.zrc.nl/api/v1/rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )
        rm.get(ROL, json=rol)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AtomicPermission.objects.for_user(self.user).count(), 1)

        atomic_permission = AtomicPermission.objects.for_user(self.user).get()

        self.assertEqual(atomic_permission.object_url, ZAAK)
        self.assertEqual(atomic_permission.object_type, PermissionObjectType.zaak)
        self.assertEqual(atomic_permission.permission, zaken_inzien.name)
