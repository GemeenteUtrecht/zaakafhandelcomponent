from unittest.mock import patch

from django.urls import reverse_lazy
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
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
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

ROL = f"{ZAKEN_ROOT}rollen/69e98129-1f0d-497f-bbfb-84b88137edbc"
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

    path = reverse_lazy("notifications:callback")

    def setUp(self):
        super().setUp()

        Service.objects.create(api_root=f"{ZAKEN_ROOT}", api_type=APITypes.zrc)
        Service.objects.create(
            api_root="https://some.ztc.nl/api/v1/", api_type=APITypes.ztc
        )

        self.user = UserFactory.create(
            username="notifs", first_name="Mona Yoko", last_name="Surname"
        )
        self.client.force_authenticate(user=self.user)

        # index zaak document
        self.zaak = factory(Zaak, ZAAK_RESPONSE)
        self.zaak.zaaktype = factory(ZaakType, ZAAKTYPE_RESPONSE)
        self.zaak_document = self.create_zaak_document(self.zaak)
        self.zaak_document.save()

        self.refresh_index()

    def test_rol_created_indexed_in_es(self, rm):
        mock_service_oas_get(rm, ZAKEN_ROOT, "zaken")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")

        self.assertEqual(self.zaak_document.rollen, [])

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
            f"{ZAKEN_ROOT}rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)
        rm.get(ROL, json=rol)

        response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=self.zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], ROL)

    def test_rol_created_add_permission_for_behandelaar(self, rm):
        # Setup mocks
        mock_service_oas_get(rm, f"{ZAKEN_ROOT}", "zaken")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)
        rm.get(ZAAK, json=ZAAK_RESPONSE)
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
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(
            f"{ZAKEN_ROOT}rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )
        rm.get(ROL, json=rol)

        response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AtomicPermission.objects.for_user(self.user).count(), 1)

        atomic_permission = AtomicPermission.objects.for_user(self.user).get()

        self.assertEqual(atomic_permission.object_url, ZAAK)
        self.assertEqual(
            atomic_permission.object_type, PermissionObjectTypeChoices.zaak
        )
        self.assertEqual(atomic_permission.permission, zaken_inzien.name)

        user_atomic_permission = atomic_permission.useratomicpermission_set.get()
        self.assertEqual(user_atomic_permission.reason, PermissionReason.betrokkene)

    def test_rol_created_destroyed_recreated_with_betrokkene_identificatie(self, rm):
        # set up mocks
        mock_service_oas_get(rm, f"{ZAKEN_ROOT}", "zaken")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)

        # Some more mocks
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
                "identificatie": self.user.username,
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
                "identificatie": self.user.username,
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(ROL, json=rol_old)
        rol_2 = factory(Rol, rol_new)

        self.assertEqual(self.zaak_document.rollen, [])

        with patch(
            "zac.core.services.update_rol", return_value=rol_2
        ) as mock_update_rol:
            with patch(
                "zac.elasticsearch.api.get_rollen", return_value=[rol_2]
            ) as mock_es_get_rollen:
                response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
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
                "url": f"{ZAKEN_ROOT}rollen/69e98129-1f0d-497f-bbfb-84b88137edbc",
                "zaak": f"{ZAKEN_ROOT}zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
            },
        )
        mock_es_get_rollen.assert_called_once_with(self.zaak)

        zaak_document = ZaakDocument.get(id=self.zaak_document.meta.id)
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

    def test_rol_created_name_not_empty(self, rm):
        """check that rol is not updated if it already has name attributes"""
        # Setup mocks
        mock_service_oas_get(rm, f"{ZAKEN_ROOT}", "zaken")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)
        rm.get(ZAAK, json=ZAAK_RESPONSE)

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
                "voorletters": "",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(
            f"{ZAKEN_ROOT}rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )
        rm.get(ROL, json=rol)

        with patch("zac.core.services.update_rol", return_value=rol) as mock_update_rol:
            response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_update_rol.assert_not_called()

        zaak_document = ZaakDocument.get(id=self.zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], ROL)
        self.assertEqual(
            zaak_document.rollen[0]["betrokkene_identificatie"],
            {
                "identificatie": "notifs",
                "voorletters": "",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        )

    def test_rol_created_username_empty(self, rm):
        """check that rol is not updated if user doesn't have first and last name"""
        empty_user = UserFactory.create(username="empty", first_name="", last_name="")
        # set up mocks
        mock_service_oas_get(rm, f"{ZAKEN_ROOT}", "zaken")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)

        # Some more mocks
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
                "identificatie": empty_user.username,
                "voorletters": "",
                "achternaam": "",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(
            f"{ZAKEN_ROOT}rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )
        rm.get(ROL, json=rol)

        with patch("zac.core.services.update_rol", return_value=rol) as mock_update_rol:
            response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_update_rol.assert_not_called()

        zaak_document = ZaakDocument.get(id=self.zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], ROL)
        self.assertEqual(
            zaak_document.rollen[0]["betrokkene_identificatie"],
            {
                "identificatie": "empty",
                "voorletters": "",
                "achternaam": "",
                "voorvoegsel_achternaam": "",
            },
        )

    def test_rol_created_other_app_updated(self, rm):
        """check there are no race conditions if several ZAC instances update rollen"""
        # set up mocks
        mock_service_oas_get(rm, f"{ZAKEN_ROOT}", "zaken")
        mock_service_oas_get(rm, "https://some.ztc.nl/api/v1/", "ztc")
        rm.get(ZAAK, json=ZAAK_RESPONSE)
        rm.get(ZAAKTYPE, json=ZAAKTYPE_RESPONSE)

        # Some more mocks
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
                "voorletters": "",
                "achternaam": "",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(ROL, json=rol)
        rol_self_updated = {
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
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rol_self_updated = factory(Rol, rol_self_updated)
        rol_other_updated = {
            "url": f"{ZAKEN_ROOT}rollen/f3ff2713-2f53-42ff-a154-16842309ad60",
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
                "voorletters": "M.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rm.get(rol_other_updated["url"], json=rol_other_updated)
        rol_other_updated = factory(Rol, rol_other_updated)

        self.assertEqual(self.zaak_document.rollen, [])

        # 1. receive rol notification with empty name
        # check that rol is updated
        with patch(
            "zac.core.services.update_rol", return_value=rol_self_updated
        ) as mock_update_rol:
            with patch(
                "zac.elasticsearch.api.get_rollen", return_value=[rol_self_updated]
            ) as mock_es_get_rollen:
                response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
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
                "url": f"{ZAKEN_ROOT}rollen/69e98129-1f0d-497f-bbfb-84b88137edbc",
                "zaak": f"{ZAKEN_ROOT}zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
            },
        )
        mock_es_get_rollen.assert_called_once_with(self.zaak)

        # 2. receive notification for the same rol with other uuid and name updated by other app
        # check that rol is not updated
        with patch(
            "zac.core.services.update_rol", return_value=rol_self_updated
        ) as mock_update_rol2:
            with patch(
                "zac.elasticsearch.api.get_rollen", return_value=[rol_other_updated]
            ) as mock_es_get_rollen2:
                other_notification = {
                    "kanaal": "zaken",
                    "hoofdObject": ZAAK,
                    "resource": "rol",
                    "resourceUrl": rol_other_updated.url,
                    "actie": "create",
                    "aanmaakdatum": timezone.now().isoformat(),
                    "kenmerken": {
                        "bronorganisatie": BRONORGANISATIE,
                        "zaaktype": ZAAKTYPE,
                        "vertrouwelijkheidaanduiding": "geheim",
                    },
                }
                response = self.client.post(self.path, other_notification)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_update_rol2.assert_not_called()
        mock_es_get_rollen2.assert_called_once_with(self.zaak)

        # check that we saved the rol updated by other app
        zaak_document = ZaakDocument.get(id=self.zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], rol_other_updated.url)
        self.assertEqual(
            zaak_document.rollen[0]["betrokkene_identificatie"],
            {
                "identificatie": "notifs",
                "voorletters": "M.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        )
