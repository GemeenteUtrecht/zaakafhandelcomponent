from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaken_add_relations, zaken_geforceerd_bijwerken
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
class ZakenRelationPermissionsTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy("manage-zaak-relation")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )

        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
            omschrijving="ZT1",
        )
        cls.hoofdzaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
            startdatum="2020-12-25",
        )
        cls.bijdragezaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630951",
            identificatie="ZAAK-2020-0011",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
            startdatum="2020-12-25",
        )
        cls.hoofdzaak["relevanteAndereZaken"] = [
            {"url": cls.bijdragezaak["url"], "aardRelatie": "vervolg"}
        ]
        cls.bijdragezaak["relevanteAndereZaken"] = [
            {"url": cls.hoofdzaak["url"], "aardRelatie": "onderwerp"}
        ]

        cls.user = UserFactory.create()
        cls.payload = {
            "bijdragezaak": cls.bijdragezaak["url"],
            "hoofdzaak": cls.hoofdzaak["url"],
            "aard_relatie": "vervolg",
            "aard_relatie_omgekeerde_richting": "onderwerp",
        }

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_login_required(self, m):
        self.client.logout()

        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.bijdragezaak)
        mock_resource_get(m, self.hoofdzaak)
        mock_resource_get(m, self.zaaktype)

        response = self.client.post(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.delete(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_to_create_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.bijdragezaak)
        mock_resource_get(m, self.hoofdzaak)
        mock_resource_get(m, self.zaaktype)

        BlueprintPermissionFactory.create(
            role__permissions=[
                zaken_add_relations.name,
            ],
            for_user=self.user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        response = self.client.post(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_to_create_but_not_for_va(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.bijdragezaak)
        mock_resource_get(m, self.hoofdzaak)
        mock_resource_get(m, self.zaaktype)

        BlueprintPermissionFactory.create(
            role__permissions=[
                zaken_add_relations.name,
            ],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        response = self.client.post(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("zac.core.api.views.ZaakRelationView.update_in_open_zaak", return_value=None)
    def test_has_perms(self, m, mock_update):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.bijdragezaak)
        mock_resource_get(m, self.hoofdzaak)
        mock_resource_get(m, self.zaaktype)

        BlueprintPermissionFactory.create(
            role__permissions=[
                zaken_add_relations.name,
            ],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_update.assert_called_once()

        response = self.client.delete(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(mock_update.call_count, 2)

    def test_has_no_force_edit_permissions_and_one_cases_are_closed(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.bijdragezaak)
        mock_resource_get(m, {**self.hoofdzaak, "einddatum": "2020-05-01"})
        mock_resource_get(m, self.zaaktype)

        BlueprintPermissionFactory.create(
            role__permissions=[
                zaken_add_relations.name,
            ],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_no_force_edit_permissions_and_cases_are_closed(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, {**self.bijdragezaak, "einddatum": "2020-05-01"})
        mock_resource_get(m, {**self.hoofdzaak, "einddatum": "2020-05-01"})
        mock_resource_get(m, self.zaaktype)

        BlueprintPermissionFactory.create(
            role__permissions=[
                zaken_add_relations.name,
            ],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("zac.core.api.views.ZaakRelationView.update_in_open_zaak", return_value=None)
    def test_has_perms_and_cases_are_closed(self, m, mock_update):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.bijdragezaak)
        mock_resource_get(m, self.hoofdzaak)
        mock_resource_get(m, self.zaaktype)

        BlueprintPermissionFactory.create(
            role__permissions=[
                zaken_add_relations.name,
                zaken_geforceerd_bijwerken.name,
            ],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.post(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_update.assert_called_once()

        response = self.client.delete(self.endpoint, self.payload)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(mock_update.call_count, 2)


@requests_mock.Mocker()
class CreateZakenRelationTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy("manage-zaak-relation")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=cls.catalogus,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
            omschrijving="ZT1",
        )
        cls.hoofdzaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
            startdatum="2020-12-25",
        )
        cls.bijdragezaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630951",
            identificatie="ZAAK-2020-0011",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
            startdatum="2020-12-25",
        )
        cls.hoofdzaak["relevanteAndereZaken"] = [
            {"url": cls.bijdragezaak["url"], "aardRelatie": "vervolg"}
        ]
        cls.bijdragezaak["relevanteAndereZaken"] = [
            {"url": cls.hoofdzaak["url"], "aardRelatie": "onderwerp"}
        ]

        cls.user = SuperUserFactory.create()
        cls.payload = {
            "bijdragezaak": cls.bijdragezaak["url"],
            "hoofdzaak": cls.hoofdzaak["url"],
            "aard_relatie": "vervolg",
            "aard_relatie_omgekeerde_richting": "onderwerp",
        }

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_valid_request(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.bijdragezaak)
        mock_resource_get(m, self.hoofdzaak)
        mock_resource_get(m, self.zaaktype)

        m.patch(self.bijdragezaak["url"], json=self.bijdragezaak)
        m.patch(self.hoofdzaak["url"], json=self.hoofdzaak)

        response = self.client.post(
            self.endpoint,
            data={
                "bijdragezaak": self.bijdragezaak["url"],
                "hoofdzaak": self.hoofdzaak["url"],
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fail_relate_zaak_to_itself(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.bijdragezaak)
        mock_resource_get(m, self.hoofdzaak)
        mock_resource_get(m, self.zaaktype)

        response = self.client.post(
            self.endpoint,
            data={
                "bijdragezaak": self.hoofdzaak["url"],
                "hoofdzaak": self.hoofdzaak["url"],
                "aard_relatie": "vervolg",
                "aard_relatie_omgekeerde_richting": "onderwerp",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
