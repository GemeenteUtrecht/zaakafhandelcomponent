from unittest.mock import patch

from django.urls import reverse_lazy
from django.utils import timezone

import requests_mock
from django_camunda.utils import underscoreize
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.accounts.constants import PermissionObjectTypeChoices, PermissionReason
from zac.accounts.models import AtomicPermission
from zac.accounts.tests.factories import UserFactory
from zac.camunda.data import Task
from zac.core.permissions import zaken_inzien
from zac.core.rollen import Rol
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CATALOGUS_RESPONSE,
    ZAAK,
    ZAAK_RESPONSE,
    ZAAKTYPE,
    ZAAKTYPE_RESPONSE,
    ZAKEN_ROOT,
)

ROLTYPE = f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac"
ROLTYPE_RESPONSE = generate_oas_component(
    "ztc",
    "schemas/RolType",
    url=ROLTYPE,
    zaaktype=ZAAKTYPE,
    omschrijving="zaak behandelaar",
    omschrijvingGeneriek="behandelaar",
)
ROL = f"{ZAKEN_ROOT}rollen/69e98129-1f0d-497f-bbfb-84b88137edbc"
ROL_RESPONSE = generate_oas_component(
    "zrc",
    "schemas/Rol",
    url=ROL,
    zaak=ZAAK,
    betrokkene="",
    betrokkeneType="medewerker",
    roltype=ROLTYPE,
    omschrijving=ROLTYPE_RESPONSE["omschrijving"],
    omschrijvingGeneriek=ROLTYPE_RESPONSE["omschrijvingGeneriek"],
    roltoelichting=ROLTYPE_RESPONSE["omschrijving"],
    registratiedatum="2020-09-01T00:00:00Z",
    indicatieMachtiging="",
    betrokkeneIdentificatie={
        "identificatie": "123456",
        "voorletters": "M.Y.",
        "achternaam": "Surname",
        "voorvoegsel_achternaam": "",
    },
)

# UPDATED: snake_case keys
NOTIFICATION = {
    "kanaal": "zaken",
    "hoofd_object": ZAAK,
    "resource": "rol",
    "resource_url": ROL,
    "actie": "create",
    "aanmaakdatum": timezone.now().isoformat(),
    "kenmerken": {
        "bronorganisatie": BRONORGANISATIE,
        "zaaktype": ZAAKTYPE,
        "vertrouwelijkheidaanduiding": "geheim",
    },
}

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
TASK_DATA = {
    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
    "name": "aName",
    "assignee": None,
    "created": "2013-01-23T13:42:42.000+0200",
    "due": "2013-01-23T13:49:42.576+0200",
    "followUp": "2013-01-23T13:44:42.437+0200",
    "delegationState": "RESOLVED",
    "description": "aDescription",
    "executionId": "anExecution",
    "owner": "anOwner",
    "parentTaskId": None,
    "priority": 42,
    "processDefinitionId": "aProcDefId",
    "processInstanceId": "87a88170-8d5c-4dec-8ee2-972a0be1b564",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": None,
    "tenantId": "aTenantId",
}


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


@requests_mock.Mocker()
class RolCreatedTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    """
    Test that the appropriate actions happen on rol-creation notifications.
    """

    path = reverse_lazy("notifications:callback")

    def setUp(self):
        super().setUp()

        ServiceFactory.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        ServiceFactory.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)

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
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)

        rol = {**ROL_RESPONSE, "betrokkeneType": "organisatorische_eenheid"}
        mock_resource_get(rm, rol)
        rm.get(
            f"{ZAKEN_ROOT}rollen?zaak={ZAAK}",
            json={"count": 1, "previous": None, "next": None, "results": [rol]},
        )

        self.assertEqual(self.zaak_document.rollen, [])
        response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        zaak_document = ZaakDocument.get(id=self.zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], ROL)

    def test_rol_created_add_permission_for_behandelaar(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        rol = {
            **ROL_RESPONSE,
            "omschrijvingGeneriek": "behandelaar",
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
        mock_resource_get(rm, rol)

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

    def test_rol_created_add_permission_for_initiator(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)
        rol = {
            **ROL_RESPONSE,
            "omschrijvingGeneriek": "initiator",
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
        mock_resource_get(rm, rol)

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
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, ROLTYPE_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)

        # Some more mocks
        rol_old = {
            **ROL_RESPONSE,
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
                "voorletters": "",
                "achternaam": "",
                "voorvoegsel_achternaam": "",
            },
        }
        rol_new_response = {
            **ROL_RESPONSE,
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        mock_resource_get(rm, rol_old)
        rm.get(ROL, json=rol_old)
        rol_new = factory(Rol, rol_new_response)
        self.assertEqual(self.zaak_document.rollen, [])

        with patch(
            "zac.core.services.update_rol", return_value=rol_new
        ) as mock_update_rol:
            with patch(
                "zac.elasticsearch.api.get_rollen", return_value=[rol_new]
            ) as mock_es_get_rollen:
                response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_update_rol.assert_called_once_with(
            ROL,
            {
                "betrokkene": "",
                "betrokkene_identificatie": {
                    "voorletters": "M.Y.",
                    "achternaam": "Surname",
                    "identificatie": "notifs",
                    "voorvoegsel_achternaam": "",
                },
                "betrokkene_type": "medewerker",
                "indicatie_machtiging": "",
                "roltoelichting": ROLTYPE_RESPONSE["omschrijving"],
                "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
                "url": ROL,
                "zaak": ZAAK,
                "roltype_omschrijving": ROLTYPE_RESPONSE["omschrijving"],
            },
            self.zaak,
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
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, ROL_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)

        rm.get(
            f"{ZAKEN_ROOT}rollen?zaak={ZAAK}",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [ROL_RESPONSE],
            },
        )

        with patch(
            "zac.core.services.update_rol", return_value=ROL_RESPONSE
        ) as mock_update_rol:
            response = self.client.post(self.path, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_update_rol.assert_not_called()

        zaak_document = ZaakDocument.get(id=self.zaak_document.meta.id)
        self.assertEqual(len(zaak_document.rollen), 1)
        self.assertEqual(zaak_document.rollen[0]["url"], ROL)
        self.assertEqual(
            zaak_document.rollen[0]["betrokkene_identificatie"],
            {
                "identificatie": "123456",
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        )

    def test_rol_created_username_empty(self, rm):
        """check that rol is not updated if user doesn't have first and last name"""
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)

        empty_user = UserFactory.create(username="empty", first_name="", last_name="")

        # Some more mocks
        rol = {
            **ROL_RESPONSE,
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
        mock_resource_get(rm, rol)

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
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, ZAAK_RESPONSE)
        mock_resource_get(rm, ZAAKTYPE_RESPONSE)
        mock_resource_get(rm, ROLTYPE_RESPONSE)
        mock_resource_get(rm, CATALOGUS_RESPONSE)

        # Some more mocks
        rol = {
            **ROL_RESPONSE,
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
                "voorletters": "",
                "achternaam": "",
                "voorvoegsel_achternaam": "",
            },
        }

        mock_resource_get(rm, rol)
        rol_self_updated = {
            **ROL_RESPONSE,
            "url": f"{ZAKEN_ROOT}rollen/some-uuid",
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        rol_self_updated = factory(Rol, rol_self_updated)

        rol_other_updated = {
            **ROL_RESPONSE,
            "url": f"{ZAKEN_ROOT}rollen/some-other-uuid",
            "betrokkeneIdentificatie": {
                "identificatie": self.user.username,
                "voorletters": "M.",
                "achternaam": "Other Surname",
                "voorvoegsel_achternaam": "",
            },
        }
        mock_resource_get(rm, rol_other_updated)
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
                "betrokkene": "",
                "betrokkene_identificatie": {
                    "voorletters": "M.Y.",
                    "achternaam": "Surname",
                    "identificatie": "notifs",
                    "voorvoegsel_achternaam": "",
                },
                "betrokkene_type": "medewerker",
                "indicatie_machtiging": "",
                "roltoelichting": ROLTYPE_RESPONSE["omschrijving"],
                "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
                "url": f"{ZAKEN_ROOT}rollen/69e98129-1f0d-497f-bbfb-84b88137edbc",
                "zaak": f"{ZAKEN_ROOT}zaken/f3ff2713-2f53-42ff-a154-16842309ad60",
                "roltype_omschrijving": ROLTYPE_RESPONSE["omschrijving"],
            },
            self.zaak,
        )
        mock_es_get_rollen.assert_called_once_with(self.zaak)

        # 2. receive notification for the same rol with other uuid and name updated by other app
        # UPDATED: snake_case keys for the second payload too
        with patch(
            "zac.core.services.update_rol", return_value=rol_self_updated
        ) as mock_update_rol2:
            with patch(
                "zac.elasticsearch.api.get_rollen", return_value=[rol_other_updated]
            ) as mock_es_get_rollen2:
                other_notification = {
                    "kanaal": "zaken",
                    "hoofd_object": ZAAK,
                    "resource": "rol",
                    "resource_url": rol_other_updated.url,
                    "actie": "create",
                    "aanmaakdatum": timezone.now().isoformat(),
                    "kenmerken": {
                        "bronorganisatie": BRONORGANISATIE,
                        "zaaktype": ZAAKTYPE,
                        "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.geheim,
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
                "achternaam": "Other Surname",
                "voorvoegsel_achternaam": "",
            },
        )
