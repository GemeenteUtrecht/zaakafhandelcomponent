from unittest.mock import patch

from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

import requests_mock
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.models import APITypes, Service

from zac.accounts.constants import PermissionObjectTypeChoices, PermissionReason
from zac.accounts.models import AtomicPermission
from zac.accounts.tests.factories import UserFactory
from zac.core.permissions import zaken_inzien
from zac.core.rollen import Rol
from zac.core.tests.utils import ClearCachesMixin
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
class RolCreatedTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    """
    Test that the appropriate actions happen on zaak-creation notifications.
    """

    def test_rol_created_indexed_in_es(self, rm):
        user = UserFactory.create(
            username="notifs", first_name="Mona Yoko", last_name="Surname"
        )
        self.client.force_authenticate(user=user)

        Service.objects.create(
            api_root="https://some.zrc.nl/api/v1/", api_type=APITypes.zrc
        )
        Service.objects.create(
            api_root="https://some.ztc.nl/api/v1/", api_type=APITypes.ztc
        )

        path = reverse("notifications:callback")

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)

        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
        rm.get(STATUS, json=STATUS_RESPONSE)

        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(STATUSTYPE, json=STATUSTYPE_RESPONSE)
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
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        rm.get(
            f"https://some.zrc.nl/api/v1/rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)
        rm.get(ROL, json=rol)

        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], ROL)

    def test_rol_created_add_permission_for_behandelaar(self, rm):
        # Setup mocks
        Service.objects.create(
            api_root="https://some.zrc.nl/api/v1/", api_type=APITypes.zrc
        )
        Service.objects.create(
            api_root="https://some.ztc.nl/api/v1/", api_type=APITypes.ztc
        )
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(STATUS, json=STATUS_RESPONSE)
        rm.get(STATUSTYPE, json=STATUSTYPE_RESPONSE)
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        user = UserFactory.create(
            username="notifs", first_name="Mona Yoko", last_name="Surname"
        )
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
                "identificatie": user.username,
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(
            f"https://some.zrc.nl/api/v1/rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )
        rm.get(ROL, json=rol)

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        zaak_document = create_zaak_document(zaak)

        self.client.force_authenticate(user=user)
        path = reverse("notifications:callback")
        response = self.client.post(path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AtomicPermission.objects.for_user(user).count(), 1)

        atomic_permission = AtomicPermission.objects.for_user(user).get()

        self.assertEqual(atomic_permission.object_url, ZAAK)
        self.assertEqual(
            atomic_permission.object_type, PermissionObjectTypeChoices.zaak
        )
        self.assertEqual(atomic_permission.permission, zaken_inzien.name)

        user_atomic_permission = atomic_permission.useratomicpermission_set.get()
        self.assertEqual(user_atomic_permission.reason, PermissionReason.betrokkene)

    def test_rol_created_destroyed_recreated_with_betrokkene_identificatie(self, rm):
        # set up mocks
        Service.objects.create(
            api_root="https://some.zrc.nl/api/v1/", api_type=APITypes.zrc
        )
        Service.objects.create(
            api_root="https://some.ztc.nl/api/v1/", api_type=APITypes.ztc
        )
        mock_service_oas_get(rm, "https://some.zrc.nl/api/v1/", "zaken")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(STATUS, json=STATUS_RESPONSE)
        rm.get(STATUSTYPE, json=STATUSTYPE_RESPONSE)
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)

        # create zaak document in ES
        zaak = factory(Zaak, ZAAK_RESPONSE)
        zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)

        # Some more mocks
        user = UserFactory.create(
            username="notifs", first_name="Mona Yoko", last_name="Surname"
        )
        rol_old = {
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
                "identificatie": user.username,
                "voorletters": "",
                "achternaam": "",
                "voorvoegsel_achternaam": "",
            },
        }

        rol_new = {
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
                "identificatie": user.username,
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(ROL, json=rol_old)
        rol_1 = factory(Rol, rol_old)
        rol_1.zaak = zaak
        rol_2 = factory(Rol, rol_new)
        rol_2.zaak = zaak

        zaak_document = create_zaak_document(zaak)
        self.assertEqual(zaak_document.rollen, [])

        self.client.force_authenticate(user=user)
        path = reverse("notifications:callback")
        with patch(
            "zac.notifications.handlers.get_rollen", return_value=[rol_1]
        ) as mock_handlers_get_rollen:
            with patch(
                "zac.core.services.get_rollen", return_value=[rol_1]
            ) as mock_services_get_rollen:
                with patch(
                    "zac.core.services.update_rol", return_value=rol_2
                ) as mock_update_rol:
                    with patch(
                        "zac.elasticsearch.api.get_rollen", return_value=[rol_2]
                    ) as mock_es_get_rollen:
                        response = self.client.post(path, NOTIFICATION)

        mock_handlers_get_rollen.assert_called_once_with(zaak)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_services_get_rollen.assert_called_once_with(zaak)
        mock_update_rol.assert_called_once_with(
            ROL,
            {
                "betrokkene": None,
                "betrokkene_identificatie": {
                    "voorletters": "M.Y.",
                    "achternaam": "Surname",
                    "identificatie": "notifs",
                    "voorvoegsel_achternaam": "",
                },
                "betrokkene_type": "medewerker",
                "indicatie_machtiging": "",
                "omschrijving": "zaak behandelaar",
                "omschrijving_generiek": "behandelaar",
                "registratiedatum": "2020-09-01T00:00:00Z",
                "roltoelichting": "some description",
                "roltype": "https://some.ztc.nl/api/v1/roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
                "url": "https://some.zrc.nl/api/v1/rollen/69e98129-1f0d-497f-bbfb-84b88137edbc",
                "zaak": "https://some.zrc.nl/api/v1/zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
            },
        )
        mock_es_get_rollen.assert_called_once_with(zaak)

        zaak_document = ZaakDocument.get(id=zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], ROL)
        self.assertEqual(
            zaak_document.rollen[0]["betrokkene_identificatie"],
            {
                "identificatie": "notifs",
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        )
