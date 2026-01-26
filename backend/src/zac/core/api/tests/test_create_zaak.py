import os
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

import requests_mock
from django_camunda.models import CamundaConfig
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import RolType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.models import CoreConfig
from zac.core.permissions import zaken_aanmaken, zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
OBJECTS_ROOT = "https://objects.nl/api/v2/"
OBJECTTYPES_ROOT = "https://objecttypes.nl/api/v2/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
class CreateZaakPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the permissions for zaak-create endpoint.

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls._zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaaktype = factory(ZaakType, cls._zaaktype)
        cls.create_zaak_url = reverse(
            "zaak-create",
        )
        cls.data = {
            "zaaktype_identificatie": cls.zaaktype.identificatie,
            "zaaktype_catalogus": CATALOGUS_URL,
            "zaak_details": {
                "omschrijving": "some-omschrijving",
                "toelichting": "some-toelichting",
            },
        }
        cls.user = UserFactory.create()

    def test_not_authenticated(self, m):
        response = self.client.post(self.create_zaak_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self._zaaktype]),
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.create_zaak_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_other_perm(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "some-other-omschrijving",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.create_zaak_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("zac.core.api.serializers.get_roltypen", return_value=[])
    def test_has_perm_to_create(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self._zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_aanmaken.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": self.zaaktype.omschrijving,
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.core.api.views.start_process",
            return_value={"instance_id": "some-uuid", "instance_url": "some-url"},
        ):
            response = self.client.post(self.create_zaak_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


@requests_mock.Mocker()
class CreateZaakResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for zaak-create endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        objects_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        objecttypes_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = objects_service
        config.primary_objecttypes_api = objecttypes_service
        config.save()

        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        cls.url = reverse(
            "zaak-create",
        )
        cls.user = SuperUserFactory.create()

        cls.data = {
            "zaaktype_identificatie": cls.zaaktype["identificatie"],
            "zaaktype_catalogus": CATALOGUS_URL,
            "zaak_details": {
                "omschrijving": "some-omschrijving",
                "toelichting": "some-toelichting",
            },
        }
        cls.objecttype = {
            "url": f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
            "uuid": "5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4",
            "name": "Some Object",
            "namePlural": "Some Objects",
            "description": "Describes the json schema of Some Object",
            "dataClassification": "open",
            "maintainerOrganization": "",
            "maintainerDepartment": "",
            "contactPerson": "",
            "contactEmail": "",
            "source": "",
            "updateFrequency": "unknown",
            "providerOrganization": "",
            "documentationUrl": "",
            "labels": {},
            "createdAt": "1999-12-31",
            "modifiedAt": "1999-12-31",
            "versions": [
                f"{OBJECTTYPES_ROOT}objecttypes/5d7182f4-dc2f-4aaa-b2a2-bdc72a2ce0b4/versions/1",
            ],
        }
        cls.object = {
            "url": f"{OBJECTS_ROOT}objects/85e6c250-9f51-4286-8340-25109d0b96d1",
            "uuid": "85e6c250-9f51-4286-8340-25109d0b96d1",
            "type": cls.objecttype["url"],
            "record": {
                "index": 1,
                "typeVersion": 1,
                "data": {"some-key": "some-val"},
                "geometry": "None",
                "startAt": "1999-12-31",
                "endAt": "None",
                "registrationAt": "1999-12-31",
                "correctionFor": "None",
                "correctedBy": "None",
            },
        }

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_create_zaak_object_does_not_exist(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")

        m.get(self.object["url"], status_code=404, json={"detail": "Not found."})
        response = self.client.post(
            self.url, {**self.data, "object": self.object["url"]}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "object",
                    "code": "invalid",
                    "reason": "Fetching OBJECT with URL: `https://objects.nl/api/v2/objects/85e6c250-9f51-4286-8340-25109d0b96d1` raised a Client Error with detail: `Not found.`.",
                }
            ],
        )

    def test_create_zaak_wrong_organisatie_rsin(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        response = self.client.post(
            self.url, {**self.data, "organisatie_rsin": "1234567890"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "organisatieRsin",
                    "code": "invalid",
                    "reason": "A RSIN has 9 digits.",
                },
                {
                    "name": "organisatieRsin",
                    "code": "max_length",
                    "reason": "Zorg ervoor dat dit veld niet meer dan 9 karakters bevat.",
                },
            ],
        )

    def test_create_zaak_zaak_omschrijving_too_long(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        response = self.client.post(
            self.url,
            {
                "zaaktype_identificatie": self.zaaktype["identificatie"],
                "zaaktype_catalogus": CATALOGUS_URL,
                "zaak_details": {
                    "omschrijving": "x" * 81,
                    "toelichting": "some-toelichting",
                },
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "zaakDetails.omschrijving",
                    "code": "max_length",
                    "reason": "Zorg ervoor dat dit veld niet meer dan 80 karakters bevat.",
                }
            ],
        )

    def test_create_zaak_zaaktype_not_found(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([]),
        )
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": f"ZAAKTYPE met `identificatie`: `{self.zaaktype['identificatie']}` kan niet worden gevonden in `{self.zaaktype['catalogus']}` of de gebruiker heeft de benodigde rechten niet.",
                }
            ],
        )

    @patch.dict(os.environ, {"DEBUG": "False"})
    @override_settings(
        CREATE_ZAAK_PROCESS_DEFINITION_KEY="some-model-that-does-not-exist"
    )
    @patch("zac.core.api.serializers.get_roltypen", return_value=[])
    def test_create_zaak_process_definition_not_found(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )

        config = CamundaConfig.get_solo()
        config.root_url = "https://camunda.example.com/"
        config.rest_api_path = "engine-rest/"
        config.save()
        m.post(
            "https://camunda.example.com/engine-rest/process-definition/key/some-model-that-does-not-exist/start",
            status_code=404,
            json={
                "type": "InvalidRequestException",
                "message": "No matching definition with id some-model-that-does-not-exist",
            },
        )
        response = self.client.post(self.url, self.data)
        self.assertEqual(
            response.json()["detail"],
            "404 Client Error: None for url: https://camunda.example.com/engine-rest/process-definition/key/some-model-that-does-not-exist/start",
        )

    @override_settings(CREATE_ZAAK_PROCESS_DEFINITION_KEY="some-model")
    def test_create_zaak(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")

        m.get(self.object["url"], json=self.object)
        m.get(self.objecttype["url"], json=self.objecttype)
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes", json=paginated_response([self.objecttype])
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/b7f920f7-ad3f-4bb3-b03f-f59a940bee4b",
            zaaktype=self.zaaktype["url"],
            omschrijving="zaak initiator",
            omschrijvingGeneriek="initiator",
        )

        config = CamundaConfig.get_solo()
        config.root_url = "https://camunda.example.com/"
        config.rest_api_path = "engine-rest/"
        config.save()
        m.post(
            "https://camunda.example.com/engine-rest/process-definition/key/some-model/start",
            status_code=201,
            json={
                "links": [{"rel": "self", "href": "https://some-url.com/"}],
                "id": "e13e72de-56ba-42b6-be36-5c280e9b30cd",
            },
        )

        # First test with roltype initiator
        with patch(
            "zac.core.api.serializers.get_roltypen",
            return_value=[factory(RolType, roltype)],
        ):
            response = self.client.post(
                self.url, {**self.data, "object": self.object["url"]}
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "instanceId": "e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "instanceUrl": "https://some-url.com/",
            },
        )

        expected_payload = {
            "businessKey": "",
            "withVariablesInReturn": False,
            "variables": {
                "zaaktypeOmschrijving": {
                    "type": "String",
                    "value": self.zaaktype["omschrijving"],
                },
                "zaaktypeIdentificatie": {
                    "type": "String",
                    "value": self.zaaktype["identificatie"],
                },
                "zaaktypeCatalogus": {
                    "type": "String",
                    "value": "http://catalogus.nl/api/v1/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                },
                "zaaktype": {
                    "type": "String",
                    "value": "http://catalogus.nl/api/v1/zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                },
                "zaakDetails": {
                    "type": "Json",
                    "value": '{"omschrijving": "some-omschrijving", "toelichting": "some-toelichting"}',
                },
                "bptlAppId": {"type": "String", "value": ""},
                "initiator": {"type": "String", "value": f"user:{self.user}"},
                "organisatieRSIN": {"type": "String", "value": "002220647"},
                "startRelatedBusinessProcess": {"type": "Boolean", "value": True},
                "objectUrl": {"type": "String", "value": self.object["url"]},
                "objectType": {"type": "String", "value": "overige"},
                "objectTypeOverige": {
                    "type": "String",
                    "value": self.objecttype["name"],
                },
            },
        }
        self.assertEqual(m.last_request.json(), expected_payload)

        # Now remove initiator from roltypes
        del expected_payload["variables"]["initiator"]
        with patch("zac.core.api.serializers.get_roltypen", return_value=[]):
            response = self.client.post(self.url, self.data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json(),
            {
                "instanceId": "e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "instanceUrl": "https://some-url.com/",
            },
        )
